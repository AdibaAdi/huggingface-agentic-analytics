"""Ingestion script for Hugging Face model/discussion data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from huggingface_hub import HfApi
from sqlalchemy import select

from config import get_config
from db import Discussion, ModelRepo, init_db, session_scope


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def ingest_data() -> dict:
    cfg = get_config()
    init_db()
    api = HfApi(token=cfg.hf_token or None)

    summary = {
        "models_seen": 0,
        "models_inserted_or_updated": 0,
        "discussions_inserted_or_updated": 0,
        "errors": [],
        "limitations": [],
    }

    with session_scope() as session:
        for tag in cfg.hf_tags:
            models = api.list_models(filter=tag, sort="downloads", direction=-1, limit=cfg.top_n_per_tag, full=True)
            for model in models:
                summary["models_seen"] += 1
                repo = session.execute(select(ModelRepo).where(ModelRepo.model_id == model.id)).scalar_one_or_none()
                if repo is None:
                    repo = ModelRepo(model_id=model.id, tag=tag)
                    session.add(repo)

                repo.tag = tag
                repo.author = getattr(model, "author", None)
                repo.likes = int(getattr(model, "likes", 0) or 0)
                repo.downloads = int(getattr(model, "downloads", 0) or 0)
                repo.pipeline_tag = getattr(model, "pipeline_tag", None)
                repo.created_at = _parse_datetime(getattr(model, "created_at", None))
                session.flush()
                summary["models_inserted_or_updated"] += 1

                try:
                    discussions = api.get_repo_discussions(repo_id=model.id, repo_type="model")
                    for d in discussions:
                        existing = session.execute(
                            select(Discussion).where(
                                Discussion.repo_id == repo.id,
                                Discussion.hf_discussion_num == int(getattr(d, "num", 0)),
                            )
                        ).scalar_one_or_none()
                        if existing is None:
                            existing = Discussion(repo_id=repo.id, hf_discussion_num=int(getattr(d, "num", 0)), title="")
                            session.add(existing)

                        existing.title = getattr(d, "title", "") or ""
                        existing.author = getattr(d, "author", None)
                        existing.is_pull_request = bool(getattr(d, "is_pull_request", False))
                        existing.status = "closed" if bool(getattr(d, "status", "") == "closed") else "open"
                        existing.created_at = _parse_datetime(getattr(d, "created_at", None))
                        existing.closed_at = _parse_datetime(getattr(d, "closed_at", None))
                        summary["discussions_inserted_or_updated"] += 1
                except Exception as exc:
                    summary["errors"].append(f"{model.id}: {exc}")

    summary["limitations"].append(
        "Hugging Face model discussions API does not provide GitHub-style commit and pull request timelines for all repos."
    )
    summary["limitations"].append(
        "Fallback used: downloads as proxy metric for forks; pull requests approximated via discussion flag is_pull_request when available."
    )
    return summary


if __name__ == "__main__":
    result = ingest_data()
    print("Ingestion completed:")
    for key, value in result.items():
        print(f"- {key}: {value}")
