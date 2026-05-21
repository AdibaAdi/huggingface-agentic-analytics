"""Derived metrics over the model and discussion tables.

The engagement score is a composite, normalized rank meant to capture
overall community activity, blending downloads, likes, and discussions into
a single comparable number per model.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from db import get_engine

ENGAGEMENT_BASE_QUERY = """
SELECT m.model_id,
       m.tag,
       m.likes,
       m.downloads,
       COALESCE(stats.total_discussions, 0)    AS total_discussions,
       COALESCE(stats.closed_discussions, 0)   AS closed_discussions,
       COALESCE(stats.open_discussions, 0)     AS open_discussions
FROM   model_repos m
LEFT   JOIN (
    SELECT repo_id,
           COUNT(*)                                              AS total_discussions,
           SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END)    AS closed_discussions,
           SUM(CASE WHEN status = 'open'   THEN 1 ELSE 0 END)    AS open_discussions
    FROM   discussions
    GROUP  BY repo_id
) stats ON stats.repo_id = m.id
"""


def _min_max_normalize(series: pd.Series) -> pd.Series:
    """Min max normalize a numeric series into [0, 1]. Returns 0 for a constant series."""
    if series.empty:
        return series
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - lo) / (hi - lo)


def engagement_table() -> pd.DataFrame:
    """Return per repo activity stats with a composite engagement score.

    ``engagement_score`` is the mean of three min-max normalized columns:
    downloads, likes, and total_discussions. Values are bounded in [0, 1].
    """
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(text(ENGAGEMENT_BASE_QUERY), conn)
    if df.empty:
        return df

    df["norm_downloads"] = _min_max_normalize(df["downloads"].astype(float))
    df["norm_likes"] = _min_max_normalize(df["likes"].astype(float))
    df["norm_discussions"] = _min_max_normalize(df["total_discussions"].astype(float))
    df["engagement_score"] = (
        df["norm_downloads"] + df["norm_likes"] + df["norm_discussions"]
    ) / 3
    df["closure_rate"] = (
        df["closed_discussions"]
        / df["total_discussions"].where(df["total_discussions"] > 0, other=pd.NA)
    ).round(3)
    return df.sort_values("engagement_score", ascending=False).reset_index(drop=True)


def top_n_by_engagement(n: int = 10) -> pd.DataFrame:
    """Return the top ``n`` repos ranked by composite engagement score."""
    df = engagement_table()
    if df.empty:
        return df
    columns = [
        "model_id",
        "tag",
        "downloads",
        "likes",
        "total_discussions",
        "closure_rate",
        "engagement_score",
    ]
    return df[columns].head(n).reset_index(drop=True)
