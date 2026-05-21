"""Transformation and cleaning step.

Takes raw rows produced by the extract layer and applies deterministic
cleaning rules:

* Strip whitespace from string fields.
* Coerce status values into the canonical lowercase set ``{"open", "closed"}``.
* Drop rows that are missing required identifiers.
* Add a ``weekday`` convenience column to discussion rows so downstream
  weekday aggregations are reproducible regardless of locale.

Each function is pure and easy to unit test.
"""

from __future__ import annotations

from typing import Any

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def clean_model_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a cleaned copy of the model rows.

    Rules:
        * ``model_id`` and ``tag`` are required. Rows without them are dropped.
        * ``likes`` and ``downloads`` are coerced to non negative integers.
        * Author and pipeline_tag are stripped to ``None`` if empty.
    """
    cleaned: list[dict[str, Any]] = []
    for r in rows:
        if not r.get("model_id") or not r.get("tag"):
            continue
        cleaned.append(
            {
                "model_id": str(r["model_id"]).strip(),
                "tag": str(r["tag"]).strip(),
                "author": _clean_optional_str(r.get("author")),
                "likes": max(int(r.get("likes") or 0), 0),
                "downloads": max(int(r.get("downloads") or 0), 0),
                "pipeline_tag": _clean_optional_str(r.get("pipeline_tag")),
                "created_at": r.get("created_at"),
                "last_modified": r.get("last_modified"),
            }
        )
    return cleaned


def clean_discussion_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a cleaned copy of the discussion rows.

    Rules:
        * ``model_id`` and ``hf_discussion_num`` are required.
        * Status is normalized to ``"open"`` or ``"closed"``.
        * A ``weekday`` field is added when ``created_at`` is present.
    """
    cleaned: list[dict[str, Any]] = []
    for r in rows:
        if not r.get("model_id") or r.get("hf_discussion_num") is None:
            continue
        status_raw = str(r.get("status") or "open").strip().lower()
        status = "closed" if status_raw == "closed" else "open"
        created_at = r.get("created_at")
        weekday = (
            WEEKDAY_NAMES[created_at.weekday()] if created_at is not None else None
        )
        cleaned.append(
            {
                "model_id": str(r["model_id"]).strip(),
                "hf_discussion_num": int(r["hf_discussion_num"]),
                "title": str(r.get("title") or "").strip(),
                "author": _clean_optional_str(r.get("author")),
                "is_pull_request": bool(r.get("is_pull_request") or False),
                "status": status,
                "created_at": created_at,
                "closed_at": r.get("closed_at"),
                "weekday": weekday,
            }
        )
    return cleaned


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def add_weekday_column(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add a ``weekday`` field to each row based on ``created_at``.

    Exposed separately because the unit tests assert on it directly.
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        copy = dict(r)
        created_at = copy.get("created_at")
        copy["weekday"] = (
            WEEKDAY_NAMES[created_at.weekday()] if created_at is not None else None
        )
        out.append(copy)
    return out
