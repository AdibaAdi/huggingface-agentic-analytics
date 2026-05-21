"""Reusable SQL queries exposed as Python helpers.

Centralizing the SQL here serves two purposes:

* The Streamlit dashboard can call these helpers directly when it does not
  need to go through the natural language agent.
* The same query strings are checked in to ``sql/03_analysis_queries.sql``
  so they can also be run with ``psql`` for reproducibility.

Each function returns a Pandas DataFrame so the caller can render it
without extra conversion.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from db import get_engine

WEEK_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# ---------------------------------------------------------------------------
# Query strings (also present in sql/03_analysis_queries.sql).
# ---------------------------------------------------------------------------

REPO_WITH_HIGHEST_DISCUSSIONS = """
SELECT m.model_id,
       COUNT(d.id) AS discussion_count
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
GROUP  BY m.model_id
ORDER  BY discussion_count DESC
"""

DISCUSSIONS_BY_REPO_BY_WEEKDAY = """
SELECT m.model_id,
       TO_CHAR(d.created_at, 'Day') AS weekday_raw,
       COUNT(*)                     AS discussion_count
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
WHERE  d.created_at IS NOT NULL
GROUP  BY m.model_id, TO_CHAR(d.created_at, 'Day')
ORDER  BY m.model_id
"""

DAY_WITH_MOST_CREATED = """
SELECT TO_CHAR(d.created_at, 'Day') AS weekday_raw,
       COUNT(*)                     AS total_discussions
FROM   discussions d
WHERE  d.created_at IS NOT NULL
GROUP  BY TO_CHAR(d.created_at, 'Day')
ORDER  BY total_discussions DESC
"""

DAY_WITH_MOST_CLOSED = """
SELECT TO_CHAR(d.closed_at, 'Day') AS weekday_raw,
       COUNT(*)                    AS closed_discussions
FROM   discussions d
WHERE  d.status = 'closed'
  AND  d.closed_at IS NOT NULL
GROUP  BY TO_CHAR(d.closed_at, 'Day')
ORDER  BY closed_discussions DESC
"""

CLOSURE_RATE_BY_REPO = """
SELECT m.model_id,
       COUNT(d.id)                                              AS total_discussions,
       SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)     AS closed_discussions,
       SUM(CASE WHEN d.status = 'open'   THEN 1 ELSE 0 END)     AS open_discussions,
       ROUND(
         SUM(CASE WHEN d.status = 'closed' THEN 1 ELSE 0 END)::numeric
         / NULLIF(COUNT(d.id), 0),
         2
       )                                                        AS closure_rate
FROM   model_repos m
LEFT   JOIN discussions d ON d.repo_id = m.id
GROUP  BY m.model_id
ORDER  BY closure_rate DESC NULLS LAST
"""

DAILY_DISCUSSIONS_OVER_TIME = """
SELECT DATE(d.created_at) AS day,
       COUNT(*)           AS total_discussions
FROM   discussions d
WHERE  d.created_at IS NOT NULL
GROUP  BY DATE(d.created_at)
ORDER  BY day
"""

DISCUSSIONS_PER_MODEL_PER_DAY = """
SELECT m.model_id,
       DATE(d.created_at) AS day,
       COUNT(*)           AS daily_discussions
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
WHERE  d.created_at IS NOT NULL
GROUP  BY m.model_id, DATE(d.created_at)
ORDER  BY m.model_id, day
"""


# ---------------------------------------------------------------------------
# Python wrappers.
# ---------------------------------------------------------------------------


def _read(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        return pd.read_sql(text(query), conn)


def _normalize_weekday(df: pd.DataFrame, col: str = "weekday_raw") -> pd.DataFrame:
    """``TO_CHAR(_, 'Day')`` pads to 9 characters. Trim and reorder."""
    if df.empty or col not in df.columns:
        return df
    out = df.copy()
    out["weekday"] = out[col].str.strip()
    out = out.drop(columns=[col])
    out["weekday"] = pd.Categorical(out["weekday"], categories=WEEK_ORDER, ordered=True)
    return out


def repo_with_highest_discussions() -> pd.DataFrame:
    return _read(REPO_WITH_HIGHEST_DISCUSSIONS)


def discussions_by_repo_by_weekday() -> pd.DataFrame:
    df = _read(DISCUSSIONS_BY_REPO_BY_WEEKDAY)
    df = _normalize_weekday(df)
    if df.empty:
        return df
    return df.sort_values(["model_id", "weekday"]).reset_index(drop=True)


def day_with_most_created() -> pd.DataFrame:
    df = _read(DAY_WITH_MOST_CREATED)
    df = _normalize_weekday(df)
    if df.empty:
        return df
    return df.sort_values("total_discussions", ascending=False).reset_index(drop=True)


def day_with_most_closed() -> pd.DataFrame:
    df = _read(DAY_WITH_MOST_CLOSED)
    df = _normalize_weekday(df)
    if df.empty:
        return df
    return df.sort_values("closed_discussions", ascending=False).reset_index(drop=True)


def closure_rate_by_repo() -> pd.DataFrame:
    return _read(CLOSURE_RATE_BY_REPO)


def daily_discussions_over_time() -> pd.DataFrame:
    return _read(DAILY_DISCUSSIONS_OVER_TIME)


def discussions_per_model_per_day() -> pd.DataFrame:
    return _read(DISCUSSIONS_PER_MODEL_PER_DAY)
