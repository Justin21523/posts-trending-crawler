"""CLI smoke tests for schema-aware commands."""

from typer.testing import CliRunner

from dcard_crawler.cli import app
from dcard_crawler.database import init_db, is_current_schema
from dcard_crawler.settings import settings


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
