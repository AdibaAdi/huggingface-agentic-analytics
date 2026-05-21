"""Time series forecasting helpers.

* Prophet powers the created and closed discussion forecasts.
* Statsmodels Exponential Smoothing powers the pull request style and
  commit proxy forecasts where Prophet would be overkill.

Both backends return Plotly figures so the Streamlit app can render them
without any backend specific code.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from prophet import Prophet
from sqlalchemy import text
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from db import get_engine

JOIN_QUERY = """
SELECT m.model_id,
       d.is_pull_request,
       d.status,
       d.created_at,
       d.closed_at
FROM   model_repos m
JOIN   discussions d ON d.repo_id = m.id
"""


def _load_joined() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(text(JOIN_QUERY), conn)
    if df.empty:
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce")
    return df


def _prophet_per_model(
    df: pd.DataFrame, date_col: str, title_prefix: str, periods: int = 14
) -> go.Figure | None:
    """One figure, one trace per model_id, with a shared time axis."""
    if df.empty:
        return None
    df = df.dropna(subset=[date_col]).copy()
    if df.empty:
        return None
    df["ds"] = df[date_col].dt.date

    fig = go.Figure()
    for model_id, group in df.groupby("model_id"):
        ts = (
            group.groupby("ds").size().reset_index(name="y").rename(columns={"ds": "ds"})
        )
        if len(ts) < 2:
            continue
        ts["ds"] = pd.to_datetime(ts["ds"])
        try:
            m = Prophet(daily_seasonality=True)
            m.fit(ts)
            future = m.make_future_dataframe(periods=periods)
            forecast = m.predict(future)
            fig.add_trace(
                go.Scatter(
                    x=forecast["ds"], y=forecast["yhat"], mode="lines",
                    name=f"{model_id} forecast",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=ts["ds"], y=ts["y"], mode="markers",
                    name=f"{model_id} actual", opacity=0.6,
                )
            )
        except Exception:
            continue

    if not fig.data:
        return None
    fig.update_layout(title=f"{title_prefix} (Prophet, +{periods} days)")
    return fig


def prophet_forecast_created() -> go.Figure | None:
    """Prophet forecast of created discussions, one trace per model."""
    df = _load_joined()
    return _prophet_per_model(df, "created_at", "Created Discussions Forecast")


def prophet_forecast_closed() -> go.Figure | None:
    """Prophet forecast of closed discussions, one trace per model."""
    df = _load_joined()
    if df.empty:
        return None
    df = df[df["status"] == "closed"]
    return _prophet_per_model(df, "closed_at", "Closed Discussions Forecast")


def _statsmodels_per_model(
    df: pd.DataFrame, date_col: str, title_prefix: str, periods: int = 7
) -> go.Figure | None:
    if df.empty:
        return None
    df = df.dropna(subset=[date_col]).copy()
    if df.empty:
        return None
    df["day"] = df[date_col].dt.date

    fig = go.Figure()
    for model_id, group in df.groupby("model_id"):
        ts = group.groupby("day").size()
        if len(ts) < 3:
            continue
        try:
            series = pd.Series(ts.values, index=pd.to_datetime(ts.index)).astype(float)
            model = ExponentialSmoothing(series, trend="add").fit()
            forecast = model.forecast(periods)
            fig.add_trace(
                go.Scatter(
                    x=series.index, y=series.values, mode="lines+markers",
                    name=f"{model_id} actual",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=forecast.index, y=forecast.values, mode="lines",
                    name=f"{model_id} forecast",
                )
            )
        except Exception:
            continue

    if not fig.data:
        return None
    fig.update_layout(title=f"{title_prefix} (Statsmodels, +{periods} days)")
    return fig


def statsmodels_forecast_pull_requests() -> go.Figure | None:
    """PR style forecast using the ``is_pull_request`` flag."""
    df = _load_joined()
    if df.empty:
        return None
    df = df[df["is_pull_request"]]
    return _statsmodels_per_model(df, "created_at", "Pull Request Activity Forecast")


def statsmodels_forecast_commits_proxy() -> go.Figure | None:
    """Commit proxy forecast. The Hub API does not expose commit timelines
    uniformly, so total discussion activity is used as a stand in proxy.
    """
    df = _load_joined()
    return _statsmodels_per_model(df, "created_at", "Commit Activity Forecast (Proxy)")
