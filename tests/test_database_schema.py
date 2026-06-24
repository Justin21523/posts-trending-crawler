"""Tests for the multi-platform database schema."""

from sqlalchemy import inspect

from dcard_crawler.database import get_engine, init_db
from dcard_crawler.settings import settings


def test_init_db_creates_multiplatform_tables(tmp_path, monkeypatch):
    """SQLite init should create Phase 1A tables."""
    db_path = tmp_path / "crawler.db"
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{db_path}")

    init_db(reset=True)

    inspector = inspect(get_engine())
    assert {"sources", "crawl_jobs", "posts", "post_metrics"}.issubset(
        set(inspector.get_table_names())
    )

    post_columns = {column["name"] for column in inspector.get_columns("posts")}
    assert {"source_id", "external_id", "platform", "content_hash"}.issubset(post_columns)

    crawl_job_columns = {column["name"] for column in inspector.get_columns("crawl_jobs")}
    assert {"error_category", "error_reason"}.issubset(crawl_job_columns)
