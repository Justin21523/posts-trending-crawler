"""Tests for FastAPI backend endpoints."""

import json
from datetime import datetime

from fastapi.testclient import TestClient

from dcard_crawler.api.app import create_app
from dcard_crawler.database import init_db
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.services.demo_seed import DemoSeedService
from dcard_crawler.settings import settings


class FakeControlService:
    async def verify_dcard(self, **kwargs):
        return fake_verify_report("dcard", "dcard")

    async def verify_ptt(self, **kwargs):
        return fake_verify_report("ptt", "ptt")

    async def verify_news_rss(self, **kwargs):
        return fake_verify_report("news", kwargs["source_name"])

    async def diagnose_dcard(self, **kwargs):
        return {
            "platform": "dcard",
            "forum": kwargs["forum"],
            "report_path": "data/reports/diagnostics/dcard_fake.json",
            "summary": {"endpoint_count": 2, "blocked_count": 1},
            "endpoints": [
                {
                    "name": "forum_posts_api",
                    "status_code": 403,
                    "policy_category": "forbidden",
                    "policy_reason": "http_403_forbidden",
                }
            ],
        }


def fake_verify_report(platform: str, source: str) -> dict:
    return {
        "platform": platform,
        "source": source,
        "job_id": 1,
        "stats": {"status": "completed", "items_stored": 1},
        "quality": {"status": "passed"},
        "report_path": f"data/reports/crawl_runs/{platform}_fake.json",
    }


def seed_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    sources = SourceRepository()
    source_id = sources.get_or_create("ptt", source_type="forum")
    PostRepository().upsert(
        NormalizedPost(
            source_id=source_id,
            source_name="ptt",
            source_type="forum",
            platform="ptt",
            external_id="M.1",
            title="AI Stock title",
            board_or_forum="Stock",
            excerpt="AI excerpt",
            content="Long enough AI content",
            published_at="2024-01-01T12:00:00",
            created_at="2024-01-01T12:00:00",
            url="https://www.ptt.cc/bbs/Stock/M.1.html",
            canonical_url="https://www.ptt.cc/bbs/Stock/M.1.html",
            raw_json={"id": "M.1"},
        )
    )
    job_id = CrawlJobRepository().start(source_id, "ptt_posts", "https://www.ptt.cc/bbs/Stock")
    CrawlJobRepository().finish(job_id, request_count=2, item_count=1)


def test_api_health_sources_posts_and_jobs(tmp_path, monkeypatch):
    seed_db(tmp_path, monkeypatch)
    client = TestClient(create_app(control_service=FakeControlService()))

    health = client.get("/health")
    sources = client.get("/sources")
    posts = client.get("/posts", params={"platform": "ptt", "keyword": "AI"})
    jobs = client.get("/crawl-jobs", params={"source": "ptt"})
    summary = client.get("/summary")
    cors = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert health.status_code == 200
    assert health.json()["database_ready"] is True
    assert sources.json()[0]["name"] == "ptt"
    assert posts.json()[0]["title"] == "AI Stock title"
    assert jobs.json()[0]["status"] == "completed"
    assert summary.json()["counts"]["posts"] == 1
    assert summary.json()["platforms"]["ptt"] == 1
    assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_api_reports_reads_json_summaries(tmp_path, monkeypatch):
    seed_db(tmp_path, monkeypatch)
    report_dir = tmp_path / "data" / "reports" / "crawl_runs"
    report_dir.mkdir(parents=True)
    report_path = report_dir / "ptt_fake.json"
    report_path.write_text(
        json.dumps(
            {
                "platform": "ptt",
                "source": "ptt",
                "generated_at": datetime.now().isoformat(),
                "job_id": 123,
                "stats": {"status": "completed"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(control_service=FakeControlService()))

    response = client.get("/reports")

    assert response.status_code == 200
    assert response.json()[0]["platform"] == "ptt"
    assert response.json()[0]["status"] == "completed"


def test_api_verify_and_diagnostics_use_control_service(tmp_path, monkeypatch):
    seed_db(tmp_path, monkeypatch)
    client = TestClient(create_app(control_service=FakeControlService()))

    dcard = client.post("/verify/dcard", json={"forum": "trending", "max_posts": 1})
    ptt = client.post(
        "/verify/ptt",
        json={"board": "Stock", "max_posts": 1, "allow_robots_unavailable": True},
    )
    news = client.post(
        "/verify/news-rss",
        json={"source_name": "demo-news", "feed_url": "https://news.example.com/rss.xml"},
    )
    diagnostics = client.post("/diagnostics/dcard", json={"forum": "trending"})

    assert dcard.status_code == 200
    assert dcard.json()["quality_status"] == "passed"
    assert ptt.json()["platform"] == "ptt"
    assert news.json()["source"] == "demo-news"
    assert diagnostics.json()["summary"]["blocked_count"] == 1


def test_api_analytics_endpoints_after_demo_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    monkeypatch.chdir(tmp_path)
    init_db(reset=True)
    DemoSeedService(report_root=tmp_path / "data" / "reports").seed(rows=120, reset_demo=True)
    client = TestClient(create_app(control_service=FakeControlService()))

    overview = client.get("/analytics/overview")
    trends = client.get("/analytics/trends")
    keywords = client.get("/analytics/keywords")
    engagement = client.get("/analytics/engagement")
    platforms = client.get("/analytics/platforms")
    quality = client.get("/analytics/data-quality")
    workflow = client.get("/workflow/summary")

    assert overview.status_code == 200
    assert overview.json()["demo_dataset_present"] is True
    assert overview.json()["kpis"]["total_posts"] == 120
    assert trends.json()["daily_post_count"]
    assert keywords.json()["keywords"]
    assert engagement.json()["top_posts"]
    assert platforms.json()["platforms"]
    assert quality.json()["demo_records"] == 120
    assert workflow.json()["stages"][0]["label"] == "Source Select"
