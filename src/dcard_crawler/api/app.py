"""FastAPI app factory for crawler portfolio UI."""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from dcard_crawler.api.schemas import (
    CrawlJobResponse,
    DashboardSummary,
    DiagnosticsDcardRequest,
    DiagnosticsResponse,
    HealthResponse,
    PostResponse,
    ReportSummary,
    SourceResponse,
    VerifyDcardRequest,
    VerifyNewsRssRequest,
    VerifyPttRequest,
    VerifyResponse,
)
from dcard_crawler.api.services import APIControlService, APIQueryService


def create_app(
    query_service: APIQueryService | None = None,
    control_service: APIControlService | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="Taiwan Public Forum & News Crawler API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    queries = query_service or APIQueryService()
    controls = control_service or APIControlService()

    @app.get("/health", response_model=HealthResponse)
    def health():
        return queries.health()

    @app.get("/sources", response_model=list[SourceResponse])
    def sources():
        return queries.list_sources()

    @app.get("/source-catalog")
    def source_catalog():
        return queries.source_catalog_status()

    @app.get("/summary", response_model=DashboardSummary)
    def summary():
        recent_jobs = [
            _crawl_job_response(job, source_name)
            for job, source_name in queries.list_crawl_jobs(limit=5)
        ]
        return {
            "counts": queries.counts(),
            "recent_jobs": recent_jobs,
            "recent_reports": queries.list_reports()[:5],
            "platforms": queries.platform_counts(),
            "health": queries.health(),
        }

    @app.get("/posts", response_model=list[PostResponse])
    def posts(
        platform: str | None = None,
        source: str | None = None,
        board_or_forum: str | None = None,
        keyword: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        rows = queries.list_posts(
            platform=platform,
            source=source,
            board_or_forum=board_or_forum,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        return [_post_response(post, source_name) for post, source_name in rows]

    @app.get("/crawl-jobs", response_model=list[CrawlJobResponse])
    def crawl_jobs(
        status: str | None = None,
        source: str | None = None,
        limit: int = Query(20, ge=1, le=100),
    ):
        return [
            _crawl_job_response(job, source_name)
            for job, source_name in queries.list_crawl_jobs(
                status=status,
                source=source,
                limit=limit,
            )
        ]

    @app.get("/reports", response_model=list[ReportSummary])
    def reports():
        return queries.list_reports()

    @app.get("/analytics/overview")
    def analytics_overview():
        return queries.analytics_overview()

    @app.get("/analytics/trends")
    def analytics_trends():
        return queries.analytics_trends()

    @app.get("/analytics/keywords")
    def analytics_keywords():
        return queries.analytics_keywords()

    @app.get("/analytics/engagement")
    def analytics_engagement():
        return queries.analytics_engagement()

    @app.get("/analytics/platforms")
    def analytics_platforms():
        return queries.analytics_platforms()

    @app.get("/analytics/data-quality")
    def analytics_data_quality():
        return queries.analytics_data_quality()

    @app.get("/analytics/dashboard")
    def analytics_dashboard():
        return queries.analytics_dashboard()

    @app.get("/analytics/time-series")
    def analytics_time_series():
        return queries.analytics_time_series()

    @app.get("/analytics/keyword-network")
    def analytics_keyword_network():
        return queries.analytics_keyword_network()

    @app.get("/analytics/keyword-heatmap")
    def analytics_keyword_heatmap():
        return queries.analytics_keyword_heatmap()

    @app.get("/analytics/source-health")
    def analytics_source_health():
        return queries.analytics_source_health()

    @app.get("/analytics/lineage")
    def analytics_lineage():
        return queries.analytics_lineage()

    @app.get("/analytics/crawl-flow")
    def analytics_crawl_flow():
        return queries.analytics_crawl_flow()

    @app.get("/analytics/top-posts")
    def analytics_top_posts():
        return queries.analytics_top_posts()

    @app.get("/analytics/data-quality-table")
    def analytics_data_quality_table():
        return queries.analytics_data_quality_table()

    @app.get("/workflow/summary")
    def workflow_summary():
        return queries.workflow_summary()

    @app.post("/verify/dcard", response_model=VerifyResponse)
    async def verify_dcard(request: VerifyDcardRequest):
        report = await controls.verify_dcard(
            forum=request.forum,
            mode=request.mode,
            max_posts=request.max_posts,
        )
        return _verify_response(report)

    @app.post("/verify/ptt", response_model=VerifyResponse)
    async def verify_ptt(request: VerifyPttRequest):
        report = await controls.verify_ptt(
            board=request.board,
            max_pages=request.max_pages,
            max_posts=request.max_posts,
            allow_robots_unavailable=request.allow_robots_unavailable,
            allow_over18_public_confirm=request.allow_over18_public_confirm,
        )
        return _verify_response(report)

    @app.post("/verify/news-rss", response_model=VerifyResponse)
    async def verify_news_rss(request: VerifyNewsRssRequest):
        report = await controls.verify_news_rss(
            source_name=request.source_name,
            feed_url=request.feed_url,
            max_articles=request.max_articles,
        )
        return _verify_response(report)

    @app.post("/diagnostics/dcard", response_model=DiagnosticsResponse)
    async def diagnostics_dcard(request: DiagnosticsDcardRequest):
        report = await controls.diagnose_dcard(
            forum=request.forum,
            sample_post_id=request.sample_post_id,
        )
        return {
            "platform": "dcard",
            "forum": report["forum"],
            "report_path": report["report_path"],
            "summary": report["summary"],
            "endpoints": report["endpoints"],
        }

    return app


def _post_response(post, source_name: str) -> dict:
    return {
        "id": post.id,
        "source": source_name,
        "source_id": post.source_id,
        "platform": post.platform,
        "external_id": post.external_id,
        "post_id": post.post_id,
        "board_or_forum": post.board_or_forum,
        "title": post.title,
        "excerpt": post.excerpt,
        "content": post.content,
        "published_at": post.published_at,
        "created_at": post.created_at,
        "crawled_at": post.crawled_at,
        "like_count": post.like_count or 0,
        "comment_count": post.comment_count or 0,
        "share_count": post.share_count or 0,
        "view_count": post.view_count or 0,
        "url": post.url,
        "canonical_url": post.canonical_url,
        "content_hash": post.content_hash,
    }


def _crawl_job_response(job, source_name: str) -> dict:
    return {
        "id": job.id,
        "source": source_name,
        "source_id": job.source_id,
        "job_type": job.job_type,
        "target_url": job.target_url,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error_category": job.error_category,
        "error_reason": job.error_reason,
        "request_count": job.request_count,
        "item_count": job.item_count,
    }


def _verify_response(report: dict) -> dict:
    stats = report.get("stats") or {}
    quality = report.get("quality") or {}
    return {
        "platform": report["platform"],
        "source": report["source"],
        "job_id": report.get("job_id"),
        "status": stats.get("status"),
        "quality_status": quality.get("status"),
        "report_path": report["report_path"],
        "stats": stats,
    }


app = create_app()
