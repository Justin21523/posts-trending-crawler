"""Compare crawler results across sources and platforms."""

import pandas as pd


def source_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate volume and engagement by source/platform."""
    columns = [
        "source",
        "platform",
        "post_count",
        "avg_engagement_score",
        "total_likes",
        "total_comments",
        "total_views",
        "first_seen",
        "last_seen",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return (
        df.groupby(["source", "platform"], dropna=False)
        .agg(
            post_count=("external_id", "nunique"),
            avg_engagement_score=("engagement_score", "mean"),
            total_likes=("like_count", "sum"),
            total_comments=("comment_count", "sum"),
            total_views=("view_count", "sum"),
            first_seen=("analysis_datetime", "min"),
            last_seen=("analysis_datetime", "max"),
        )
        .reset_index()
        .sort_values("post_count", ascending=False)
    )
