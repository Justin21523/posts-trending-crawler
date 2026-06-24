"""CLI smoke tests for schema-aware commands."""

import csv
import json

from typer.testing import CliRunner

from dcard_crawler.cli import app
from dcard_crawler.database import init_db, is_current_schema
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.settings import settings


class FakeIngestService:
    calls = []
    connector = None

    async def crawl_posts(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "posts_listed": 1,
            "posts_detailed": 0,
            "posts_stored": 1,
            "posts_skipped": 0,
            "errors": 0,
        }

    async def close(self):
        return None

    async def crawl_target(self, target, **kwargs):
        self.calls.append({"target": target, **kwargs})
        return {
            "items_listed": 1,
            "items_detailed": 1,
            "items_stored": 1,
            "items_skipped": 0,
            "errors": 0,
        }


class FakePttConnector:
    @staticmethod
    def board_target(board):
        from dcard_crawler.connectors.base import ConnectorTarget

        return ConnectorTarget(url=f"https://www.ptt.cc/bbs/{board}/index.html", label=board)


class FakePttIngestService(FakeIngestService):
    connector = FakePttConnector()


class FakeNewsIngestService(FakeIngestService):
    connector = None


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


def test_dcard_alias_commands_pass_expected_fetch_details(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    fake_service = FakeIngestService()
    fake_service.calls = []
    monkeypatch.setattr("dcard_crawler.cli.build_ingest_service", lambda: fake_service)

    runner = CliRunner()
    list_result = runner.invoke(app, ["crawl-dcard-list", "--mode", "popular", "--no-resume"])
    posts_result = runner.invoke(app, ["crawl-dcard-posts", "--mode", "latest", "--no-resume"])
    default_result = runner.invoke(app, ["crawl-dcard", "--no-resume"])

    assert list_result.exit_code == 0
    assert posts_result.exit_code == 0
    assert default_result.exit_code == 0
    assert fake_service.calls[0]["fetch_details"] is False
    assert fake_service.calls[0]["popular"] is True
    assert fake_service.calls[1]["fetch_details"] is True
    assert fake_service.calls[1]["popular"] is False
    assert fake_service.calls[2]["fetch_details"] is True


def test_discover_and_verify_dcard_help_commands_run():
    runner = CliRunner()

    discover_result = runner.invoke(app, ["discover-dcard-endpoints", "--help"])
    verify_result = runner.invoke(app, ["verify-dcard-endpoints", "--help"])

    assert discover_result.exit_code == 0
    assert verify_result.exit_code == 0


def test_crawl_ptt_uses_service_factory_without_live_network(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    fake_service = FakePttIngestService()
    fake_service.calls = []
    monkeypatch.setattr("dcard_crawler.cli.build_ptt_ingest_service", lambda **kwargs: fake_service)

    result = CliRunner().invoke(app, ["crawl-ptt", "--board", "Stock", "--max-pages", "1"])

    assert result.exit_code == 0
    assert "PTT crawl completed" in result.output
    assert fake_service.calls[0]["target"].label == "Stock"


def test_news_commands_use_service_factory_without_live_network(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    fake_service = FakeNewsIngestService()
    fake_service.calls = []
    monkeypatch.setattr(
        "dcard_crawler.cli.build_news_ingest_service",
        lambda **kwargs: fake_service,
    )

    runner = CliRunner()
    rss_result = runner.invoke(
        app,
        [
            "crawl-news-rss",
            "--source-name",
            "demo",
            "--feed-url",
            "https://news.example.com/rss.xml",
        ],
    )
    sitemap_result = runner.invoke(
        app,
        [
            "crawl-news-sitemap",
            "--source-name",
            "demo",
            "--sitemap-url",
            "https://news.example.com/sitemap.xml",
        ],
    )
    article_result = runner.invoke(
        app,
        [
            "crawl-news-article",
            "--source-name",
            "demo",
            "--url",
            "https://news.example.com/a",
        ],
    )

    assert rss_result.exit_code == 0
    assert sitemap_result.exit_code == 0
    assert article_result.exit_code == 0
    assert fake_service.calls[0]["target"].metadata["target_type"] == "rss"
    assert fake_service.calls[1]["target"].metadata["target_type"] == "sitemap"
    assert fake_service.calls[2]["target"].metadata["target_type"] == "article"


def test_news_help_commands_run():
    runner = CliRunner()

    assert runner.invoke(app, ["crawl-news-rss", "--help"]).exit_code == 0
    assert runner.invoke(app, ["crawl-news-sitemap", "--help"]).exit_code == 0
    assert runner.invoke(app, ["crawl-news-article", "--help"]).exit_code == 0


def test_status_shows_recent_crawl_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    jobs = CrawlJobRepository()
    job_id = jobs.start(source_id, "dcard_posts", "https://www.dcard.tw/f/trending")
    jobs.fail(
        job_id,
        error_message="blocked",
        request_count=1,
        item_count=0,
        error_category="robots_disallowed",
        error_reason="robots.txt disallows URL",
    )

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Recent crawl jobs" in result.output
    assert "robots_disallowed" in result.output


def test_export_outputs_consistent_jsonl_and_csv_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    PostRepository().upsert(
        NormalizedPost(
            source_id=source_id,
            platform="dcard",
            external_id="12345",
            post_id=12345,
            forum_alias="trending",
            board_or_forum="trending",
            title="Export title",
            excerpt="Export excerpt",
            content="Export content long enough",
            published_at="2024-01-01T12:00:00Z",
            created_at="2024-01-01T12:00:00Z",
            like_count=2,
            comment_count=1,
            url="https://www.dcard.tw/f/trending/p/12345",
            canonical_url="https://www.dcard.tw/f/trending/p/12345",
            content_hash="abc123",
            raw_json={"id": 12345},
        )
    )

    jsonl_path = tmp_path / "posts.jsonl"
    csv_path = tmp_path / "posts.csv"
    runner = CliRunner()
    jsonl_result = runner.invoke(app, ["export", "--format", "jsonl", "--output", str(jsonl_path)])
    csv_result = runner.invoke(app, ["export", "--format", "csv", "--output", str(csv_path)])

    assert jsonl_result.exit_code == 0
    assert csv_result.exit_code == 0
    json_record = json.loads(jsonl_path.read_text().splitlines()[0])
    with open(csv_path, newline="", encoding="utf-8") as f:
        csv_record = next(csv.DictReader(f))

    expected_fields = {"board_or_forum", "published_at", "crawled_at", "content_hash"}
    assert expected_fields.issubset(json_record)
    assert expected_fields.issubset(csv_record)


def test_export_outputs_news_row(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    source_id = SourceRepository().get_or_create("demo-news", source_type="news")
    PostRepository().upsert(
        NormalizedPost(
            source_id=source_id,
            source_name="demo-news",
            source_type="news",
            platform="news",
            external_id="hash-id",
            title="News title",
            board_or_forum="社會",
            excerpt="News summary",
            content="News content long enough",
            published_at="2024-01-01T12:00:00Z",
            created_at="2024-01-01T12:00:00Z",
            url="https://news.example.com/a",
            canonical_url="https://news.example.com/a",
            content_hash="news-hash",
            raw_json={"url": "https://news.example.com/a"},
        )
    )

    output_path = tmp_path / "news.jsonl"
    result = CliRunner().invoke(
        app,
        ["export", "--format", "jsonl", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    record = json.loads(output_path.read_text().splitlines()[0])
    assert record["platform"] == "news"
    assert record["source"] == "demo-news"
    assert record["board_or_forum"] == "社會"
