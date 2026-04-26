"""Plotly charts and forecast helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
from prophet import Prophet
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from analytics_queries import _load_discussions_df


def _base_df() -> pl.DataFrame:
    return _load_discussions_df()


def line_total_discussions_over_time():
    df = _base_df().filter(pl.col("created_at").is_not_null())
    if df.is_empty():
        return None
    chart_df = (
        df.with_columns(pl.col("created_at").dt.date().alias("date"))
        .group_by("date")
        .agg(pl.count("hf_discussion_num").alias("total_discussions"))
        .sort("date")
        .to_pandas()
    )
    return px.line(chart_df, x="date", y="total_discussions", title="Total Discussions Over Time")


def pie_discussions_distribution_by_model():
    df = _base_df().filter(pl.col("hf_discussion_num").is_not_null())
    if df.is_empty():
        return None
    chart_df = df.group_by("model_id").agg(pl.count("hf_discussion_num").alias("total")).to_pandas()
    return px.pie(chart_df, names="model_id", values="total", title="Discussion Distribution by Model")


def bar_likes_per_model():
    df = _base_df()
    if df.is_empty():
        return None
    chart_df = df.group_by("model_id").agg(pl.max("likes").alias("likes")).to_pandas()
    return px.bar(chart_df, x="model_id", y="likes", title="Likes by Model")


def bar_downloads_per_model():
    df = _base_df()
    if df.is_empty():
        return None
    chart_df = df.group_by("model_id").agg(pl.max("downloads").alias("downloads")).to_pandas()
    return px.bar(chart_df, x="model_id", y="downloads", title="Downloads by Model (Forks Fallback)")


def bar_closed_discussions_per_week():
    df = _base_df().filter((pl.col("status") == "closed") & pl.col("closed_at").is_not_null())
    if df.is_empty():
        return None
    chart_df = (
        df.with_columns(pl.col("closed_at").dt.strftime("%Y-W%W").alias("year_week"))
        .group_by("year_week")
        .agg(pl.count("hf_discussion_num").alias("closed_count"))
        .sort("year_week")
        .to_pandas()
    )
    return px.bar(chart_df, x="year_week", y="closed_count", title="Closed Discussions per Week")


def stacked_open_closed_per_model():
    df = _base_df().filter(pl.col("hf_discussion_num").is_not_null())
    if df.is_empty():
        return None
    chart_df = (
        df.group_by(["model_id", "status"]).agg(pl.count("hf_discussion_num").alias("count")).to_pandas()
    )
    return px.bar(chart_df, x="model_id", y="count", color="status", barmode="stack", title="Open vs Closed")


def prophet_forecast_created_per_model(model_id: str, periods: int = 14):
    df = _base_df().filter((pl.col("model_id") == model_id) & pl.col("created_at").is_not_null())
    if df.is_empty():
        return None
    ts = (
        df.with_columns(pl.col("created_at").dt.date().alias("ds"))
        .group_by("ds")
        .agg(pl.count("hf_discussion_num").alias("y"))
        .sort("ds")
        .to_pandas()
    )
    if len(ts) < 2:
        return None
    m = Prophet(daily_seasonality=True)
    m.fit(ts)
    future = m.make_future_dataframe(periods=periods)
    fc = m.predict(future)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], name="Forecast"))
    fig.add_trace(go.Scatter(x=ts["ds"], y=ts["y"], name="Actual"))
    fig.update_layout(title=f"Prophet Forecast (Created Discussions): {model_id}")
    return fig


def prophet_forecast_closed_per_model(model_id: str, periods: int = 14):
    df = _base_df().filter((pl.col("model_id") == model_id) & (pl.col("status") == "closed") & pl.col("closed_at").is_not_null())
    if df.is_empty():
        return None
    ts = (
        df.with_columns(pl.col("closed_at").dt.date().alias("ds"))
        .group_by("ds")
        .agg(pl.count("hf_discussion_num").alias("y"))
        .sort("ds")
        .to_pandas()
    )
    if len(ts) < 2:
        return None
    m = Prophet(daily_seasonality=True)
    m.fit(ts)
    future = m.make_future_dataframe(periods=periods)
    fc = m.predict(future)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], name="Forecast"))
    fig.add_trace(go.Scatter(x=ts["ds"], y=ts["y"], name="Actual"))
    fig.update_layout(title=f"Prophet Forecast (Closed Discussions): {model_id}")
    return fig


def statsmodels_placeholder_forecast(model_id: str, metric: str):
    """Fallback/limitation chart for PRs and commits where HF may not expose full data."""

    df = _base_df().filter(pl.col("model_id") == model_id)
    if df.is_empty():
        return None, f"No data for {model_id}."

    if metric == "pull_requests":
        ts = (
            df.filter(pl.col("is_pull_request") == True)
            .filter(pl.col("created_at").is_not_null())
            .with_columns(pl.col("created_at").dt.date().alias("date"))
            .group_by("date")
            .agg(pl.count("hf_discussion_num").alias("value"))
            .sort("date")
            .to_pandas()
        )
        title = "Statsmodels Forecast (PR-like discussions)"
        limitation = "HF discussions use is_pull_request flag when present; this is not equivalent to GitHub PR history."
    else:
        ts = (
            df.filter(pl.col("created_at").is_not_null())
            .with_columns(pl.col("created_at").dt.date().alias("date"))
            .group_by("date")
            .agg(pl.count("hf_discussion_num").alias("value"))
            .sort("date")
            .to_pandas()
        )
        title = "Statsmodels Forecast (Commits fallback)"
        limitation = "HF API does not provide commit timeline in this workflow; using discussion activity as fallback signal."

    if len(ts) < 3:
        return None, f"Not enough history for {metric}. {limitation}"

    series = ts.set_index("date")["value"].astype(float)
    model = ExponentialSmoothing(series, trend="add").fit()
    forecast = model.forecast(7)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, name="Actual"))
    fig.add_trace(go.Scatter(x=forecast.index, y=forecast.values, name="Forecast"))
    fig.update_layout(title=f"{title}: {model_id}")
    return fig, limitation
