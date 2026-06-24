"""Trend analysis helpers."""

import pandas as pd


def daily_post_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Count posts by date, platform, and board/forum."""
    if df.empty:
        return pd.DataFrame(columns=["date", "platform", "board_or_forum", "post_count"])
    return (
        df.groupby(["date", "platform", "board_or_forum"], dropna=False)
        .size()
        .reset_index(name="post_count")
        .sort_values(["date", "post_count"], ascending=[True, False])
    )


def weekly_post_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Count posts by week and platform."""
    if df.empty:
        return pd.DataFrame(columns=["week", "platform", "post_count"])
    return (
        df.groupby(["week", "platform"], dropna=False)
        .size()
        .reset_index(name="post_count")
        .sort_values(["week", "post_count"], ascending=[True, False])
    )


def top_boards(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """Return most active boards/forums."""
    if df.empty:
        return pd.DataFrame(columns=["platform", "board_or_forum", "post_count"])
    return (
        df.groupby(["platform", "board_or_forum"], dropna=False)
        .size()
        .reset_index(name="post_count")
        .sort_values("post_count", ascending=False)
        .head(limit)
    )
