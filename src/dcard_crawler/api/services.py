"""Read/query and crawler-control services for the FastAPI backend."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, or_, select

from dcard_crawler.connectors.base import ConnectorTarget
from dcard_crawler.database import get_session, is_current_schema
from dcard_crawler.models import CrawlJob, Post, Source
from dcard_crawler.services.dcard_diagnostics import DcardEndpointDiagnosticsService
from dcard_crawler.services.factory import (
    build_ingest_service,
    build_news_ingest_service,
    build_ptt_ingest_service,
)
from dcard_crawler.services.live_verification import LiveVerificationService


class APIQueryService:
    """Query SQLite data for API responses."""

    def health(self) -> dict[str, Any]:
        """Return backend health and schema status."""
        return {"status": "ok", "database_ready": is_current_schema()}

    def list_sources(self) -> list[Source]:
        """Return all configured data sources."""
        with get_session() as session:
            return list(session.execute(select(Source).order_by(Source.name)).scalars().all())

    def list_posts(
        self,
        *,
        platform: str | None = None,
        source: str | None = None,
        board_or_forum: str | None = None,
        keyword: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[Post, str]]:
        """Return posts with source names using simple portfolio UI filters."""
        with get_session() as session:
            query = select(Post, Source.name).join(Source, Source.id == Post.source_id)
            if platform:
                query = query.where(Post.platform == platform)
            if source:
                query = query.where(Source.name == source)
            if board_or_forum:
                query = query.where(Post.board_or_forum == board_or_forum)
            if keyword:
                pattern = f"%{keyword}%"
                query = query.where(
                    or_(
                        Post.title.ilike(pattern),
                        Post.excerpt.ilike(pattern),
                        Post.content.ilike(pattern),
                    )
                )
            if date_from:
                query = query.where(
                    or_(Post.published_at >= date_from, Post.created_at >= date_from)
                )
            if date_to:
                query = query.where(or_(Post.published_at <= date_to, Post.created_at <= date_to))
            query = query.order_by(desc(Post.crawled_at)).limit(limit).offset(offset)
            return list(session.execute(query).all())

    def list_crawl_jobs(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[tuple[CrawlJob, str]]:
        """Return recent crawl jobs with source names."""
        with get_session() as session:
            query = select(CrawlJob, Source.name).join(Source, Source.id == CrawlJob.source_id)
            if status:
                query = query.where(CrawlJob.status == status)
            if source:
                query = query.where(Source.name == source)
            query = query.order_by(desc(CrawlJob.started_at)).limit(limit)
            return list(session.execute(query).all())

    def list_reports(self, report_root: str | Path = "data/reports") -> list[dict[str, Any]]:
        """Return summaries for report JSON files."""
        root = Path(report_root)
        if not root.exists():
            return []

        summaries = []
        report_paths = sorted(
            root.glob("*/*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in report_paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            stats = payload.get("stats") or {}
            summaries.append(
                {
                    "path": str(path),
                    "report_type": path.parent.name,
                    "platform": payload.get("platform"),
                    "source": payload.get("source"),
                    "generated_at": payload.get("generated_at"),
                    "job_id": payload.get("job_id"),
                    "status": stats.get("status") or payload.get("summary", {}).get("status"),
                }
            )
        return summaries

    def counts(self) -> dict[str, int]:
        """Return dashboard-ready table counts."""
        with get_session() as session:
            return {
                "sources": int(session.execute(select(func.count(Source.id))).scalar() or 0),
                "posts": int(session.execute(select(func.count(Post.id))).scalar() or 0),
                "crawl_jobs": int(session.execute(select(func.count(CrawlJob.id))).scalar() or 0),
            }


class APIControlService:
    """Run crawler verification and diagnostics for API endpoints."""

    async def verify_dcard(self, *, forum: str, mode: str, max_posts: int) -> dict[str, Any]:
        """Run Dcard live verification."""
        verifier = LiveVerificationService()
        return await verifier.verify_dcard(
            build_ingest_service(),
            forum=forum,
            popular=mode == "popular",
            max_posts=max_posts,
        )

    async def verify_ptt(
        self,
        *,
        board: str,
        max_pages: int,
        max_posts: int,
        allow_robots_unavailable: bool,
        allow_over18_public_confirm: bool,
    ) -> dict[str, Any]:
        """Run PTT live verification."""
        service = build_ptt_ingest_service(
            board=board,
            allow_over18_public_confirm=allow_over18_public_confirm,
            robots_unavailable_policy="allow" if allow_robots_unavailable else None,
        )
        verifier = LiveVerificationService()
        return await verifier.verify_connector(
            service,
            platform="ptt",
            source_name="ptt",
            target=service.connector.board_target(board),
            max_pages=max_pages,
            max_posts=max_posts,
            source_base_url="https://www.ptt.cc",
            robots_url="https://www.ptt.cc/robots.txt",
            metadata={
                "robots_unavailable_policy_override": allow_robots_unavailable,
                "robots_unavailable_policy": "allow" if allow_robots_unavailable else "block",
            },
        )

    async def verify_news_rss(
        self,
        *,
        source_name: str,
        feed_url: str,
        max_articles: int,
    ) -> dict[str, Any]:
        """Run News RSS live verification."""
        service = build_news_ingest_service(source_name=source_name)
        target = ConnectorTarget(
            url=feed_url,
            label=source_name,
            metadata={"target_type": "rss"},
        )
        verifier = LiveVerificationService()
        return await verifier.verify_connector(
            service,
            platform="news",
            source_name=source_name,
            target=target,
            max_pages=1,
            max_posts=max_articles,
            max_articles=max_articles,
            source_base_url=feed_url,
        )

    async def diagnose_dcard(
        self,
        *,
        forum: str,
        sample_post_id: int | None = None,
    ) -> dict[str, Any]:
        """Run Dcard endpoint diagnostics."""
        return await DcardEndpointDiagnosticsService().diagnose(
            forum=forum,
            sample_post_id=sample_post_id,
        )
