"""Data quality checks run against the loaded PostgreSQL tables.

The Streamlit Data Quality page renders these results so reviewers can
verify that the underlying dataset is trustworthy before reading the
analysis.

Every check returns a count of offending rows. Zero is the success case.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from db import get_engine

VALID_STATUSES = {"open", "closed"}


def run_all_checks() -> pd.DataFrame:
    """Run every check and return a single summary DataFrame.

    Columns: ``check_name``, ``offending_rows``, ``description``.
    """
    engine = get_engine()

    with engine.begin() as conn:
        models = pd.read_sql(text("SELECT * FROM model_repos"), conn)
        discussions = pd.read_sql(text("SELECT * FROM discussions"), conn)

    return pd.DataFrame(
        [
            {
                "check_name": "models.total_rows",
                "offending_rows": len(models),
                "description": "Total model rows loaded (informational, not a failure).",
            },
            {
                "check_name": "discussions.total_rows",
                "offending_rows": len(discussions),
                "description": "Total discussion rows loaded (informational, not a failure).",
            },
            {
                "check_name": "models.missing_model_id",
                "offending_rows": int(models["model_id"].isna().sum())
                if not models.empty
                else 0,
                "description": "Rows in model_repos missing model_id.",
            },
            {
                "check_name": "discussions.missing_repo_id",
                "offending_rows": int(discussions["repo_id"].isna().sum())
                if not discussions.empty
                else 0,
                "description": "Discussions with no parent repo id.",
            },
            {
                "check_name": "discussions.missing_created_at",
                "offending_rows": int(discussions["created_at"].isna().sum())
                if not discussions.empty
                else 0,
                "description": "Discussions with no creation timestamp.",
            },
            {
                "check_name": "discussions.duplicate_per_repo",
                "offending_rows": int(
                    discussions.duplicated(
                        subset=["repo_id", "hf_discussion_num"]
                    ).sum()
                )
                if not discussions.empty
                else 0,
                "description": "Duplicate (repo_id, hf_discussion_num) pairs.",
            },
            {
                "check_name": "discussions.invalid_status_values",
                "offending_rows": int(
                    (~discussions["status"].isin(VALID_STATUSES)).sum()
                )
                if not discussions.empty
                else 0,
                "description": "Status values outside the canonical set {open, closed}.",
            },
            {
                "check_name": "discussions.closed_before_created",
                "offending_rows": _count_closed_before_created(discussions),
                "description": "Discussions whose closed_at precedes created_at.",
            },
            {
                "check_name": "models.negative_likes",
                "offending_rows": int((models["likes"] < 0).sum())
                if not models.empty
                else 0,
                "description": "Repos with negative like counts (should be impossible).",
            },
            {
                "check_name": "models.negative_downloads",
                "offending_rows": int((models["downloads"] < 0).sum())
                if not models.empty
                else 0,
                "description": "Repos with negative download counts (should be impossible).",
            },
        ]
    )


def _count_closed_before_created(discussions: pd.DataFrame) -> int:
    if discussions.empty:
        return 0
    mask = discussions["closed_at"].notna() & discussions["created_at"].notna() & (
        discussions["closed_at"] < discussions["created_at"]
    )
    return int(mask.sum())


# Pure functions, isolated for unit testing without a database connection.

def validate_discussions(df: pd.DataFrame) -> dict[str, int]:
    """Return a count dictionary of common issues in a discussions DataFrame."""
    if df.empty:
        return {
            "missing_model_id": 0,
            "missing_created_at": 0,
            "duplicate_discussions": 0,
            "invalid_status_values": 0,
        }
    return {
        "missing_model_id": int(df["model_id"].isna().sum())
        if "model_id" in df.columns
        else 0,
        "missing_created_at": int(df["created_at"].isna().sum())
        if "created_at" in df.columns
        else 0,
        "duplicate_discussions": int(
            df.duplicated(
                subset=[c for c in ("model_id", "hf_discussion_num") if c in df.columns]
            ).sum()
        ),
        "invalid_status_values": int(
            (~df["status"].isin(VALID_STATUSES)).sum()
        )
        if "status" in df.columns
        else 0,
    }
