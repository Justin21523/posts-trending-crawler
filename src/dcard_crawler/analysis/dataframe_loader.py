"""Load crawler data into pandas DataFrames."""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, select

from dcard_crawler.database import get_engine
from dcard_crawler.models import Post, Source

STANDARD_COLUMNS = [
    "source",
    "platform",
    "external_id",
    "post_id",
    "forum_alias",
    "board_or_forum",
    "title",
    "excerpt",
    "content",
    "published_at",
    "created_at",
    "crawled_at",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
    "url",
    "canonical_url",
    "content_hash",
]


def load_posts_dataframe(input_path: str | Path | None = None) -> pd.DataFrame:
    """Load posts from SQLite, CSV, JSONL, or Excel."""
    if input_path is None:
        return load_posts_from_sqlite()

    path = Path(input_path)
    suffix = path.suffix.lower()
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        return load_posts_from_sqlite(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported input format: {path}")


def load_posts_from_sqlite(db_path: str | Path | None = None) -> pd.DataFrame:
    """Load normalized posts from the configured SQLite database or a DB file."""
    engine = get_engine() if db_path is None else create_engine(f"sqlite:///{db_path}")
    query = (
        select(
            Source.name.label("source"),
            Post.platform,
            Post.external_id,
            Post.post_id,
            Post.forum_alias,
            Post.board_or_forum,
            Post.title,
            Post.excerpt,
            Post.content,
            Post.published_at,
            Post.created_at,
            Post.crawled_at,
            Post.like_count,
            Post.comment_count,
            Post.share_count,
            Post.view_count,
            Post.url,
            Post.canonical_url,
            Post.content_hash,
        )
        .join(Source, Source.id == Post.source_id)
        .order_by(Post.crawled_at.desc())
    )
    return pd.read_sql_query(query, engine)


def ensure_standard_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with all analysis columns present."""
    result = df.copy()
    for column in STANDARD_COLUMNS:
        if column not in result.columns:
            result[column] = None
    return result[STANDARD_COLUMNS + [c for c in result.columns if c not in STANDARD_COLUMNS]]
