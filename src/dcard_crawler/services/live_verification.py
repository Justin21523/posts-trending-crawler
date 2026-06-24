"""Live crawl verification and data quality reporting."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select

from dcard_crawler.connectors.base import ConnectorTarget
from dcard_crawler.database import get_session
from dcard_crawler.models import Post, Source
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.services.dcard_diagnostics import DcardEndpointDiagnosticsService
from dcard_crawler.services.ingest_service import IngestService


@dataclass(frozen=True)
class QualityThresholds:
    """Thresholds for a small live verification run."""

    min_title_ratio: float = 0.9
    min_content_ratio: float = 0.6
    min_url_ratio: float = 0.9
    min_published_at_ratio: float = 0.5
    max_duplicate_ratio: float = 0.2


class DataQualityGate:
    """Summarize whether recently stored posts look complete enough."""

    def __init__(self, thresholds: QualityThresholds | None = None):
        self.thresholds = thresholds or QualityThresholds()

    def evaluate(self, posts: list[Post], attempted_items: int) -> dict[str, Any]:
        """Return a pass/warn/fail quality summary."""
        total = len(posts)
        if attempted_items <= 0:
            return {
                "status": "failed",
                "total_posts": 0,
                "issues": ["no items were listed"],
                "ratios": {},
            }
        if total == 0:
            return {
                "status": "failed",
                "total_posts": 0,
                "issues": ["no posts were stored"],
                "ratios": {},
            }

        ratios = {
            "title_non_empty": self._ratio(posts, lambda post: bool((post.title or "").strip())),
            "content_non_empty": self._ratio(
                posts,
                lambda post: bool((post.content or post.excerpt or "").strip()),
            ),
            "url_non_empty": self._ratio(posts, lambda post: bool((post.url or "").strip())),
            "published_at_non_empty": self._ratio(
                posts,
                lambda post: bool((post.published_at or post.created_at or "").strip()),
            ),
            "content_hash_non_empty": self._ratio(
                posts,
                lambda post: bool((post.content_hash or "").strip()),
            ),
            "duplicate_ratio": self._duplicate_ratio(posts),
        }
        issues = self._issues(ratios)
        status = "passed"
        if issues:
            status = "warning"
        if ratios["title_non_empty"] < 0.5 or ratios["url_non_empty"] < 0.5:
            status = "failed"
        return {
            "status": status,
            "total_posts": total,
            "attempted_items": attempted_items,
            "issues": issues,
            "ratios": ratios,
        }

    def _issues(self, ratios: dict[str, float]) -> list[str]:
        issues = []
        thresholds = self.thresholds
        if ratios["title_non_empty"] < thresholds.min_title_ratio:
            issues.append("title non-empty ratio is low")
        if ratios["content_non_empty"] < thresholds.min_content_ratio:
            issues.append("content/excerpt non-empty ratio is low")
        if ratios["url_non_empty"] < thresholds.min_url_ratio:
            issues.append("url non-empty ratio is low")
        if ratios["published_at_non_empty"] < thresholds.min_published_at_ratio:
            issues.append("published_at/created_at ratio is low")
        if ratios["duplicate_ratio"] > thresholds.max_duplicate_ratio:
            issues.append("duplicate ratio is high")
        return issues

    @staticmethod
    def _ratio(posts: list[Post], predicate) -> float:
        if not posts:
            return 0.0
        return round(sum(1 for post in posts if predicate(post)) / len(posts), 4)

    @staticmethod
    def _duplicate_ratio(posts: list[Post]) -> float:
        keys = [post.content_hash or f"{post.platform}:{post.external_id}" for post in posts]
        if not keys:
            return 0.0
        return round((len(keys) - len(set(keys))) / len(keys), 4)


class LiveVerificationService:
    """Run low-volume live crawler smoke checks and write reports."""

    def __init__(
        self,
        *,
        report_dir: str | Path = "data/reports/crawl_runs",
        quality_gate: DataQualityGate | None = None,
        crawl_jobs: CrawlJobRepository | None = None,
        dcard_diagnostics: DcardEndpointDiagnosticsService | None = None,
    ):
        self.report_dir = Path(report_dir)
        self.quality_gate = quality_gate or DataQualityGate()
        self.crawl_jobs = crawl_jobs or CrawlJobRepository()
        self.dcard_diagnostics = dcard_diagnostics or DcardEndpointDiagnosticsService()

    async def verify_dcard(
        self,
        service: IngestService,
        *,
        forum: str = "trending",
        max_posts: int = 5,
        popular: bool = False,
    ) -> dict[str, Any]:
        """Run a small Dcard live verification crawl."""
        try:
            stats = await service.crawl_posts(
                forum_alias=forum,
                max_posts=max_posts,
                popular=popular,
                fetch_details=True,
                resume=False,
            )
            diagnostics = None
            if stats.get("status") == "failed":
                diagnostics = await self.dcard_diagnostics.diagnose(forum=forum)
            return self._build_and_write_report(
                platform="dcard",
                source_name="dcard",
                target=forum,
                stats=stats,
                attempted_items=int(stats.get("posts_listed", 0)),
                metadata={"dcard_diagnostics": diagnostics} if diagnostics else None,
            )
        finally:
            await service.close()

    async def verify_connector(
        self,
        service: ConnectorIngestService,
        *,
        platform: str,
        source_name: str,
        target: ConnectorTarget,
        max_pages: int = 1,
        max_posts: int = 5,
        source_base_url: str | None = None,
        robots_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        **listing_kwargs,
    ) -> dict[str, Any]:
        """Run a small connector verification crawl."""
        try:
            stats = await service.crawl_target(
                target,
                max_pages=max_pages,
                max_posts=max_posts,
                fetch_details=True,
                source_base_url=source_base_url,
                robots_url=robots_url,
                **listing_kwargs,
            )
            return self._build_and_write_report(
                platform=platform,
                source_name=source_name,
                target=target.url,
                stats=stats,
                attempted_items=int(stats.get("items_listed", 0)),
                metadata=metadata,
            )
        finally:
            await service.close()

    def _build_and_write_report(
        self,
        *,
        platform: str,
        source_name: str,
        target: str,
        stats: dict[str, Any],
        attempted_items: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        posts = self._recent_posts(
            source_name=source_name,
            platform=platform,
            limit=attempted_items,
        )
        quality = self.quality_gate.evaluate(posts, attempted_items=attempted_items)
        samples = self._samples(posts)
        report = {
            "platform": platform,
            "source": source_name,
            "target": target,
            "job_id": stats.get("job_id"),
            "started_at": stats.get("started_at"),
            "completed_at": stats.get("completed_at"),
            "generated_at": datetime.now().isoformat(),
            "stats": stats,
            "quality": quality,
            "samples": samples,
            "metadata": metadata or {},
        }

        if stats.get("status") == "completed" and quality["status"] in {"warning", "failed"}:
            reason = "; ".join(quality["issues"]) or "data quality warning"
            report["stats"]["status"] = "completed_with_warnings"
            self.crawl_jobs.warn(
                int(stats["job_id"]),
                warning_message=reason,
                request_count=self._request_count(stats),
                item_count=self._stored_count(stats),
                error_reason=reason,
            )

        report_path = self._write_report(platform, stats.get("job_id"), report)
        report["report_path"] = str(report_path)
        return report

    def _recent_posts(self, source_name: str, platform: str, limit: int) -> list[Post]:
        if limit <= 0:
            return []
        with get_session() as session:
            return list(
                session.execute(
                    select(Post)
                    .join(Source, Source.id == Post.source_id)
                    .where(Source.name == source_name, Post.platform == platform)
                    .order_by(desc(Post.crawled_at))
                    .limit(limit)
                )
                .scalars()
                .all()
            )

    @staticmethod
    def _samples(posts: list[Post]) -> list[dict[str, Any]]:
        return [
            {
                "external_id": post.external_id,
                "title": post.title,
                "url": post.url,
                "content_length": len(post.content or post.excerpt or ""),
            }
            for post in posts[:5]
        ]

    def _write_report(self, platform: str, job_id: int | None, report: dict[str, Any]) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.report_dir / f"{platform}_{job_id or 'unknown'}_{timestamp}.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _request_count(stats: dict[str, Any]) -> int:
        return int(stats.get("request_count") or 0)

    @staticmethod
    def _stored_count(stats: dict[str, Any]) -> int:
        return int(stats.get("posts_stored") or stats.get("items_stored") or 0)
