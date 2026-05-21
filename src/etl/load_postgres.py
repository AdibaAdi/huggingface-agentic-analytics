"""Load step: idempotently upsert cleaned rows into PostgreSQL.

The load step is the only place in the pipeline that talks to the database
for writes. It uses SQLAlchemy ORM upserts keyed on the natural primary
identifiers (``model_id`` for models, ``(repo_id, hf_discussion_num)`` for
discussions) so the entire pipeline can be safely re-run.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from db import Discussion, ModelRepo, init_db, session_scope
from utils.logging_utils import get_logger

_log = get_logger(__name__)


def load_models(rows: list[dict[str, Any]]) -> int:
    """Upsert model rows. Returns the number of rows touched."""
    init_db()
    touched = 0
    with session_scope() as session:
        for r in rows:
            repo = session.execute(
                select(ModelRepo).where(ModelRepo.model_id == r["model_id"])
            ).scalar_one_or_none()
            if repo is None:
                repo = ModelRepo(model_id=r["model_id"], tag=r["tag"])
                session.add(repo)
            repo.tag = r["tag"]
            repo.author = r.get("author")
            repo.likes = r.get("likes", 0)
            repo.downloads = r.get("downloads", 0)
            repo.pipeline_tag = r.get("pipeline_tag")
            repo.created_at = r.get("created_at")
            repo.last_modified = r.get("last_modified")
            touched += 1
    _log.info("Upserted %d model rows", touched)
    return touched


def load_discussions(rows: list[dict[str, Any]]) -> int:
    """Upsert discussion rows. Returns the number of rows touched.

    Each discussion row carries a ``model_id`` (string) which is resolved to
    the parent ``model_repos.id`` (integer) at load time. Rows whose parent
    repo is not present in the database are skipped.
    """
    touched = 0
    with session_scope() as session:
        # Build a lookup of model_id -> id once.
        repos = session.execute(select(ModelRepo)).scalars().all()
        repo_lookup = {r.model_id: r.id for r in repos}

        for r in rows:
            repo_pk = repo_lookup.get(r["model_id"])
            if repo_pk is None:
                continue
            existing = session.execute(
                select(Discussion).where(
                    Discussion.repo_id == repo_pk,
                    Discussion.hf_discussion_num == int(r["hf_discussion_num"]),
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = Discussion(
                    repo_id=repo_pk,
                    hf_discussion_num=int(r["hf_discussion_num"]),
                    title=r.get("title", ""),
                )
                session.add(existing)
            existing.title = r.get("title", "")
            existing.author = r.get("author")
            existing.is_pull_request = bool(r.get("is_pull_request", False))
            existing.status = r.get("status", "open")
            existing.created_at = r.get("created_at")
            existing.closed_at = r.get("closed_at")
            touched += 1
    _log.info("Upserted %d discussion rows", touched)
    return touched
