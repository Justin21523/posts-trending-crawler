"""Engagement scoring for cross-platform posts."""

import pandas as pd


def add_engagement_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add a simple reproducible engagement score."""
    result = df.copy()
    result["engagement_score"] = (
        result["like_count"]
        + result["comment_count"] * 2
        + result["share_count"] * 3
        + result["view_count"] * 0.01
    )
    return result


def top_posts(df: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    """Return top posts by engagement score."""
    columns = [
        "source",
        "platform",
        "board_or_forum",
        "date",
        "title",
        "url",
        "like_count",
        "comment_count",
        "share_count",
        "view_count",
        "engagement_score",
    ]
    available = [column for column in columns if column in df.columns]
    return df.sort_values("engagement_score", ascending=False).head(limit)[available]
