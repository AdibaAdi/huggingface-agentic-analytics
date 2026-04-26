"""Deterministic analytics queries for required assignment prompts."""

from __future__ import annotations

import polars as pl
from sqlalchemy import text

from db import get_engine

WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _load_discussions_df() -> pl.DataFrame:
    engine = get_engine()
    query = """
    SELECT m.model_id, m.likes, m.downloads,
           d.hf_discussion_num, d.status, d.is_pull_request,
           d.created_at, d.closed_at
    FROM model_repos m
    LEFT JOIN discussions d ON d.repo_id = m.id
    """
    with engine.begin() as conn:
        pdf = pl.read_database(query=text(query), connection=conn)
    if pdf.is_empty():
        return pdf
    return pdf.with_columns(
        pl.col("created_at").cast(pl.Datetime, strict=False),
        pl.col("closed_at").cast(pl.Datetime, strict=False),
    )


def repo_with_highest_discussions() -> tuple[str, pl.DataFrame]:
    df = _load_discussions_df()
    if df.is_empty():
        return "No data available. Run ingestion first.", pl.DataFrame()
    table = (
        df.filter(pl.col("hf_discussion_num").is_not_null())
        .group_by("model_id")
        .agg(pl.count("hf_discussion_num").alias("discussion_count"))
        .sort("discussion_count", descending=True)
    )
    top = table.row(0)
    return f"Repo with highest discussions: {top[0]} ({top[1]} discussions)", table


def discussions_by_repo_by_weekday() -> tuple[str, pl.DataFrame]:
    df = _load_discussions_df()
    if df.is_empty():
        return "No data available. Run ingestion first.", pl.DataFrame()
    table = (
        df.filter(pl.col("created_at").is_not_null())
        .with_columns(pl.col("created_at").dt.strftime("%A").alias("weekday"))
        .group_by(["model_id", "weekday"])
        .agg(pl.count("hf_discussion_num").alias("discussion_count"))
    )
    weekday_order_df = pl.DataFrame({"weekday": WEEK_ORDER, "weekday_order": list(range(7))})
    table = (
        table.join(weekday_order_df, on="weekday", how="left")
        .sort(["model_id", "weekday_order"])
        .drop("weekday_order")
    )
    return "Daily discussion totals by repo.", table


def day_with_most_discussions_created() -> tuple[str, pl.DataFrame]:
    df = _load_discussions_df()
    if df.is_empty():
        return "No data available. Run ingestion first.", pl.DataFrame()
    table = (
        df.filter(pl.col("created_at").is_not_null())
        .with_columns(pl.col("created_at").dt.strftime("%A").alias("weekday"))
        .group_by("weekday")
        .agg(pl.count("hf_discussion_num").alias("total_discussions"))
        .sort("total_discussions", descending=True)
    )
    top = table.row(0)
    return f"Highest created discussions day: {top[0]} ({top[1]}).", table


def day_with_most_discussions_closed() -> tuple[str, pl.DataFrame]:
    df = _load_discussions_df()
    if df.is_empty():
        return "No data available. Run ingestion first.", pl.DataFrame()
    table = (
        df.filter((pl.col("status") == "closed") & pl.col("closed_at").is_not_null())
        .with_columns(pl.col("closed_at").dt.strftime("%A").alias("weekday"))
        .group_by("weekday")
        .agg(pl.count("hf_discussion_num").alias("closed_discussions"))
        .sort("closed_discussions", descending=True)
    )
    if table.is_empty():
        return "No closed discussions available.", table
    top = table.row(0)
    return f"Highest closed discussions day: {top[0]} ({top[1]}).", table


def resolve_action(action: str) -> tuple[str, pl.DataFrame]:
    mapping = {
        "highest_discussions": repo_with_highest_discussions,
        "table_discussions_weekday": discussions_by_repo_by_weekday,
        "day_most_created": day_with_most_discussions_created,
        "day_most_closed": day_with_most_discussions_closed,
    }
    handler = mapping.get(action)
    if handler is None:
        return "Unsupported action. Try a required query.", pl.DataFrame()
    return handler()
