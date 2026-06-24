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
    def run_demo_workflow(self, **kwargs):
        rows = kwargs.get("rows", 120)
        if rows > 1000:
            return {
                "posts_inserted": rows,
                "sources_inserted": 3,
                "jobs_inserted": 0,
                "reports_inserted": 0,
                "mode": "parameter_validation_only",
            }
        return DemoSeedService().seed(
            rows=rows,
            reset_demo=kwargs.get("reset_demo", True),
        )

    def generate_excel_report(self, **kwargs):
        from dcard_crawler.analysis.excel_report import export_analysis_report

        output_path = kwargs.get("output_path", "data/exports/test_report.xlsx")
        tables = export_analysis_report(None, output_path, "configs/keywords.txt", None)
        return {
            "status": "completed",
            "output_path": output_path,
            "download_url": f"/reports/download?path={output_path}",
            "row_count": len(tables["Raw Data"]),
            "keyword_match_count": len(tables["Keyword Matches"]),
            "sheets": list(tables),
        }

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


def test_api_source_catalog_merges_database_status(tmp_path, monkeypatch):
    seed_db(tmp_path, monkeypatch)
    client = TestClient(create_app(control_service=FakeControlService()))

    response = client.get("/source-catalog")
    payload = response.json()

    assert response.status_code == 200
    assert any(item["name"] == "cna-technology" for item in payload)
    assert all("database_backed" in item for item in payload)


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


def test_api_visualization_endpoints_after_demo_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    monkeypatch.chdir(tmp_path)
    init_db(reset=True)
    DemoSeedService(report_root=tmp_path / "data" / "reports").seed(rows=120, reset_demo=True)
    client = TestClient(create_app(control_service=FakeControlService()))

    dashboard = client.get("/analytics/dashboard")
    time_series = client.get("/analytics/time-series")
    network = client.get("/analytics/keyword-network")
    keyword_insights = client.get("/analytics/keyword-insights")
    heatmap = client.get("/analytics/keyword-heatmap")
    source_health = client.get("/analytics/source-health")
    lineage = client.get("/analytics/lineage")
    crawl_flow = client.get("/analytics/crawl-flow")
    top_posts = client.get("/analytics/top-posts")
    quality_table = client.get("/analytics/data-quality-table")

    assert dashboard.status_code == 200
    assert dashboard.json()["daily_platform_volume"]
    assert time_series.json()["daily_by_platform"]
    assert network.json()["nodes"]
    assert "insight_summary" in network.json()["nodes"][0]
    assert keyword_insights.json()["cards"]
    assert heatmap.json()["cells"]
    assert source_health.json()["rows"]
    assert lineage.json()["nodes"]
    assert lineage.json()["nodes"][0]["label_zh"]
    assert crawl_flow.json()["nodes"][0]["data"]["label"] == "Source Select"
    assert crawl_flow.json()["nodes"][0]["data"]["label_zh"] == "選擇資料來源"
    assert crawl_flow.json()["nodes"][1]["data"]["compliance"]
    assert top_posts.json()["rows"]
    assert "missing_content" in quality_table.json()


def test_api_demo_story_and_run_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    monkeypatch.chdir(tmp_path)
    init_db(reset=True)
    client = TestClient(create_app(control_service=FakeControlService()))

    run = client.post("/demo/workflow/run", params={"rows": 120, "reset_demo": True})
    run_large = client.post("/demo/workflow/run", params={"rows": 10000, "reset_demo": True})
    story = client.get("/analytics/demo-story")
    posts = client.get("/posts", params={"source": "demo-ptt", "limit": 5})

    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert run.json()["stats"]["posts_inserted"] == 120
    assert run_large.status_code == 200
    assert run_large.json()["stats"]["posts_inserted"] == 10000
    assert story.status_code == 200
    assert story.json()["walkthrough_steps"][0]["label"] == "Source Select"
    assert story.json()["architecture"]["nodes"]
    assert story.json()["lifecycle"]["edges"]
    assert any(
        "fail-closed" in step["compliance"]
        for step in story.json()["walkthrough_steps"]
    )
    assert posts.json()


def test_api_posts_search_and_drilldown(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    monkeypatch.chdir(tmp_path)
    init_db(reset=True)
    DemoSeedService(report_root=tmp_path / "data" / "reports").seed(rows=120, reset_demo=True)
    client = TestClient(create_app(control_service=FakeControlService()))

    search = client.get("/posts/search", params={"platform": "ptt", "limit": 10, "offset": 0})
    payload = search.json()
    post_id = payload["rows"][0]["id"]
    post_drilldown = client.get("/analytics/drilldown", params={"kind": "post", "id": post_id})
    source_drilldown = client.get(
        "/analytics/drilldown",
        params={"kind": "source", "id": payload["rows"][0]["source"]},
    )
    keyword_drilldown = client.get("/analytics/drilldown", params={"kind": "keyword", "id": "AI"})
    workflow_drilldown = client.get(
        "/analytics/drilldown",
        params={"kind": "workflow_node", "id": "policy_check"},
    )

    assert search.status_code == 200
    assert payload["total"] >= 10
    assert payload["rows"]
    assert payload["facets"]["platforms"]
    assert post_drilldown.json()["metadata"]["id"] == post_id
    assert post_drilldown.json()["related_jobs"]
    assert source_drilldown.json()["summary"]["post_count"] > 0
    assert keyword_drilldown.json()["related_posts"]
    assert "http_403_forbidden" in workflow_drilldown.json()["quality_flags"]


def test_api_compliance_excel_and_metadata_payloads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    monkeypatch.chdir(tmp_path)
    init_db(reset=True)
    DemoSeedService(report_root=tmp_path / "data" / "reports").seed(rows=120, reset_demo=True)
    client = TestClient(create_app(control_service=FakeControlService()))

    network = client.get("/analytics/keyword-network")
    compliance = client.get("/analytics/compliance-summary")
    report = client.post("/reports/excel", params={"output": "data/exports/test_report.xlsx"})
    drilldown = client.get(
        "/analytics/drilldown",
        params={"kind": "report", "id": "data/exports/test_report.xlsx"},
    )

    assert network.status_code == 200
    assert {
        "category",
        "color",
        "metadata",
        "platform_distribution",
        "top_related_terms",
        "evidence_posts",
    }.issubset(network.json()["nodes"][0])
    assert compliance.status_code == 200
    assert compliance.json()["summary"]["source_count"] > 0
    assert compliance.json()["governance_rules"]
    assert report.status_code == 200
    assert report.json()["status"] == "completed"
    assert report.json()["download_url"].startswith("/reports/download")
    download = client.get(report.json()["download_url"])
    blocked_download = client.get("/reports/download", params={"path": "pyproject.toml"})
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert blocked_download.status_code == 403
    assert (tmp_path / "data" / "exports" / "test_report.xlsx").exists()
    assert drilldown.json()["metadata_status"] == "available"
    assert drilldown.json()["available_fields"]
    assert drilldown.json()["related_posts"]
    assert drilldown.json()["related_jobs"]


def test_api_allows_vite_fallback_dev_ports():
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5176",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5176"
