"""Investigation oriented anomaly detection.

Flags days where a single model received an unusually large number of new
discussions relative to its own recent rolling history. This is a simple
baseline detector intended to surface obvious spikes, not a statistical
hypothesis test.

The threshold is the rolling 7 day mean multiplied by a configurable
sensitivity (default 2.0).
"""

from __future__ import annotations

import pandas as pd

from analysis.sql_queries import discussions_per_model_per_day


def detect_discussion_spikes(
    window: int = 7, multiplier: float = 2.0, min_daily: int = 3
) -> pd.DataFrame:
    """Return rows where a model's daily discussion count is anomalously high.

    Args:
        window: Size of the trailing rolling window in days.
        multiplier: A day is flagged when daily count exceeds the rolling
            mean times this multiplier.
        min_daily: Minimum daily discussion count required for a row to be
            considered a candidate spike. Filters out trivially small days.

    Returns:
        Pandas DataFrame with columns
        ``model_id, day, daily_discussions, rolling_avg, spike_ratio``.
    """
    df = discussions_per_model_per_day()
    if df.empty:
        return df

    df["day"] = pd.to_datetime(df["day"])
    df = df.sort_values(["model_id", "day"]).reset_index(drop=True)

    df["rolling_avg"] = (
        df.groupby("model_id")["daily_discussions"]
        .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
    )
    df["spike_ratio"] = df["daily_discussions"] / df["rolling_avg"].where(
        df["rolling_avg"] > 0, other=pd.NA
    )

    spikes = df[
        (df["daily_discussions"] >= min_daily)
        & (df["spike_ratio"] >= multiplier)
    ].copy()
    spikes["rolling_avg"] = spikes["rolling_avg"].round(2)
    spikes["spike_ratio"] = spikes["spike_ratio"].round(2)
    return spikes.sort_values("spike_ratio", ascending=False).reset_index(drop=True)
