"""CLI smoke tests for schema-aware commands."""

from typer.testing import CliRunner

from dcard_crawler.cli import app
from dcard_crawler.database import init_db, is_current_schema
from dcard_crawler.settings import settings


class FakeIngestService:
    async def crawl_posts(self, **kwargs):
        return {
            "posts_listed": 1,
            "posts_detailed": 0,
            "posts_stored": 1,
            "posts_skipped": 0,
            "errors": 0,
        }

    async def close(self):
        return None


def test_init_reset_creates_current_schema(tmp_path, monkeypatch):
    """CLI init --reset should create the current multi-platform schema."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")

    result = CliRunner().invoke(app, ["init", "--reset"])

    assert result.exit_code == 0
    assert is_current_schema() is True


def test_status_runs_on_fresh_multiplatform_db(tmp_path, monkeypatch):
    """Status should run against a fresh Phase 1A schema."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert "No posts in database yet" in result.output


def test_export_runs_with_no_posts(tmp_path, monkeypatch):
    """Export should handle an empty fresh database without failing."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    result = CliRunner().invoke(app, ["export", "--output", str(tmp_path / "posts.jsonl")])

    assert result.exit_code == 0
    assert "No posts to export" in result.output


def test_crawl_list_uses_service_factory_without_live_network(tmp_path, monkeypatch):
    """crawl-list should assemble service through the factory path."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    monkeypatch.setattr("dcard_crawler.cli.build_ingest_service", lambda: FakeIngestService())

    result = CliRunner().invoke(app, ["crawl-list", "--max-posts", "1", "--no-resume"])

    assert result.exit_code == 0
    assert "Crawl completed" in result.output


def test_crawl_posts_uses_service_factory_without_live_network(tmp_path, monkeypatch):
    """crawl-posts should assemble service through the factory path."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    monkeypatch.setattr("dcard_crawler.cli.build_ingest_service", lambda: FakeIngestService())

    result = CliRunner().invoke(app, ["crawl-posts", "--max-posts", "1", "--no-resume"])

    assert result.exit_code == 0
    assert "Crawl completed" in result.output
