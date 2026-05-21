"""Extract step: fetch community discussions for every tracked model repository.

A community discussion in Hugging Face terms includes both regular issue
style threads and pull requests. The ``is_pull_request`` flag from the API
is preserved so the analysis layer can distinguish the two.

Some repositories disable discussions entirely or restrict them, which the
Hub API surfaces as a 403. Those failures are captured per repo and returned
alongside the rows so the caller can decide what to do.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from huggingface_hub import HfApi

from config import AppConfig
from utils.logging_utils import get_logger

_log = get_logger(__name__)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def extract_discussions_for_repo(
    cfg: AppConfig, model_id: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Return discussions for one repo plus an optional error message.

    The error message is set when the Hub API returns a non success status
    (typically a 403 for repos that have discussions disabled).
    """
    api = HfApi(token=cfg.hf_token or None)
    rows: list[dict[str, Any]] = []
    try:
        for d in api.get_repo_discussions(repo_id=model_id, repo_type="model"):
            status_raw = getattr(d, "status", "open")
            status = "closed" if str(status_raw).lower() == "closed" else "open"
            rows.append(
                {
                    "model_id": model_id,
                    "hf_discussion_num": int(getattr(d, "num", 0) or 0),
                    "title": getattr(d, "title", "") or "",
                    "author": getattr(d, "author", None),
                    "is_pull_request": bool(
                        getattr(d, "is_pull_request", False) or False
                    ),
                    "status": status,
                    "created_at": _parse_datetime(getattr(d, "created_at", None)),
                    "closed_at": _parse_datetime(getattr(d, "closed_at", None)),
                }
            )
        _log.debug("Fetched %d discussions for %s", len(rows), model_id)
        return rows, None
    except Exception as exc:
        msg = f"{model_id}: {exc}"
        _log.warning("Discussion fetch failed for %s", msg)
        return rows, msg
