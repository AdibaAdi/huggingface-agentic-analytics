"""Extract step: fetch the top N Hugging Face model repositories for each tag.

This module is intentionally side effect free with respect to the database.
It calls the public Hugging Face Hub API, normalizes the response into a list
of plain dictionaries, and returns them. The load step is responsible for
upserting these rows into PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from huggingface_hub import HfApi

from config import AppConfig
from utils.logging_utils import get_logger

_log = get_logger(__name__)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a value into a naive ``datetime`` or ``None`` if not parseable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def extract_top_models(cfg: AppConfig) -> list[dict[str, Any]]:
    """Return the top ``cfg.top_n_per_tag`` models for each configured tag.

    Each dictionary in the returned list has the shape expected by
    :func:`src.etl.load_postgres.upsert_model_repo`.
    """
    api = HfApi(token=cfg.hf_token or None)
    rows: list[dict[str, Any]] = []

    for tag in cfg.hf_tags:
        _log.info("Fetching top %d models for tag '%s'", cfg.top_n_per_tag, tag)
        models: Iterable[Any] = api.list_models(
            filter=tag,
            sort="downloads",
            limit=cfg.top_n_per_tag,
            full=True,
        )
        for model in models:
            rows.append(
                {
                    "model_id": model.id,
                    "tag": tag,
                    "author": getattr(model, "author", None),
                    "likes": int(getattr(model, "likes", 0) or 0),
                    "downloads": int(getattr(model, "downloads", 0) or 0),
                    "pipeline_tag": getattr(model, "pipeline_tag", None),
                    "created_at": _parse_datetime(getattr(model, "created_at", None)),
                    "last_modified": _parse_datetime(
                        getattr(model, "last_modified", None)
                    ),
                }
            )
    _log.info("Extracted %d model rows across %d tags", len(rows), len(cfg.hf_tags))
    return rows
