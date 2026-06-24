"""Read/query and crawler-control services for the FastAPI backend."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, or_, select

from dcard_crawler.connectors.base import ConnectorTarget
from dcard_crawler.core.text_utils import normalize_text
from dcard_crawler.database import get_session, is_current_schema
from dcard_crawler.models import CrawlJob, Post, Source
from dcard_crawler.services.dcard_diagnostics import DcardEndpointDiagnosticsService
from dcard_crawler.services.demo_seed import DEMO_KEYWORDS
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

    def platform_counts(self) -> dict[str, int]:
        """Return post counts grouped by platform."""
        with get_session() as session:
            rows = session.execute(
                select(Post.platform, func.count(Post.id)).group_by(Post.platform)
            ).all()
            return {platform: int(count) for platform, count in rows}

    def analytics_overview(self) -> dict[str, Any]:
        """Return high-level portfolio analytics for the overview dashboard."""
        with get_session() as session:
            total_posts = int(session.execute(select(func.count(Post.id))).scalar() or 0)
            total_jobs = int(session.execute(select(func.count(CrawlJob.id))).scalar() or 0)
            successful_jobs = int(
                session.execute(
                    select(func.count(CrawlJob.id)).where(
                        CrawlJob.status.in_(["completed", "completed_with_warnings"])
                    )
                ).scalar()
                or 0
            )
            failed_jobs = int(
                session.execute(
                    select(func.count(CrawlJob.id)).where(CrawlJob.status == "failed")
                ).scalar()
                or 0
            )
            missing_content = int(
                session.execute(
                    select(func.count(Post.id)).where(
                        or_(Post.content.is_(None), Post.content == "")
                    )
                ).scalar()
                or 0
            )
            duplicate_hashes = self._duplicate_hash_count(session)
            top_posts = self._top_posts(session, limit=8)
            keyword_stats = self._keyword_counts(session, limit=8)
            platforms = [
                {"platform": platform, "count": count}
                for platform, count in sorted(self.platform_counts().items())
            ]

        parse_success_rate = (
            round(((total_posts - missing_content) / total_posts) * 100, 1) if total_posts else 0
        )
        duplicate_rate = round((duplicate_hashes / total_posts) * 100, 1) if total_posts else 0
        return {
            "demo_dataset_present": self._has_demo_dataset(),
            "kpis": {
                "total_sources": self.counts()["sources"],
                "total_posts": total_posts,
                "successful_crawl_runs": successful_jobs,
                "failed_crawl_runs": failed_jobs,
                "parse_success_rate": parse_success_rate,
                "duplicate_rate": duplicate_rate,
                "total_crawl_runs": total_jobs,
            },
            "platforms": platforms,
            "top_keywords": keyword_stats,
            "top_posts": top_posts,
            "latest_jobs": [
                self._job_dict(job, source_name)
                for job, source_name in self.list_crawl_jobs(limit=8)
            ],
        }

    def analytics_trends(self) -> dict[str, Any]:
        """Return daily post volume grouped by platform."""
        daily: dict[tuple[str, str], int] = defaultdict(int)
        board_counts: Counter[str] = Counter()
        with get_session() as session:
            rows = session.execute(
                select(Post.platform, Post.board_or_forum, Post.published_at)
            ).all()
        for platform, board, published_at in rows:
            day = self._date_key(published_at)
            if day:
                daily[(day, platform)] += 1
            if board:
                board_counts[board] += 1
        points = [
            {"date": day, "platform": platform, "count": count}
            for (day, platform), count in sorted(daily.items())
        ]
        return {
            "daily_post_count": points,
            "top_boards": [
                {"board_or_forum": board, "count": count}
                for board, count in board_counts.most_common(12)
            ],
        }

    def analytics_keywords(self) -> dict[str, Any]:
        """Return keyword frequency and platform distribution."""
        keyword_counts: Counter[str] = Counter()
        by_platform: dict[str, Counter[str]] = defaultdict(Counter)
        with get_session() as session:
            rows = session.execute(
                select(Post.platform, Post.title, Post.excerpt, Post.content)
            ).all()
        for platform, title, excerpt, content in rows:
            text = normalize_text(" ".join([title or "", excerpt or "", content or ""]))
            for keyword in DEMO_KEYWORDS:
                count = text.count(normalize_text(keyword))
                if count:
                    keyword_counts[keyword] += count
                    by_platform[platform][keyword] += count
        return {
            "keywords": [
                {"keyword": keyword, "count": count}
                for keyword, count in keyword_counts.most_common(20)
            ],
            "by_platform": [
                {"platform": platform, "keyword": keyword, "count": count}
                for platform, counter in sorted(by_platform.items())
                for keyword, count in counter.most_common(10)
            ],
        }

    def analytics_engagement(self) -> dict[str, Any]:
        """Return engagement score summaries."""
        with get_session() as session:
            rows = session.execute(
                select(Post, Source.name).join(Source, Source.id == Post.source_id)
            ).all()
        scored = []
        missing_metrics = Counter()
        for post, source_name in rows:
            if not post.like_count:
                missing_metrics["like_count"] += 1
            if not post.comment_count:
                missing_metrics["comment_count"] += 1
            if not post.view_count:
                missing_metrics["view_count"] += 1
            scored.append(self._post_engagement_dict(post, source_name))
        scored.sort(key=lambda item: item["engagement_score"], reverse=True)
        by_platform: dict[str, list[float]] = defaultdict(list)
        for item in scored:
            by_platform[item["platform"]].append(item["engagement_score"])
        return {
            "top_posts": scored[:20],
            "missing_metrics": dict(missing_metrics),
            "average_score_by_platform": [
                {
                    "platform": platform,
                    "average_engagement_score": round(sum(scores) / len(scores), 2),
                }
                for platform, scores in sorted(by_platform.items())
                if scores
            ],
        }

    def analytics_platforms(self) -> dict[str, Any]:
        """Return cross-platform comparison data."""
        stats: dict[str, dict[str, Any]] = {}
        with get_session() as session:
            rows = session.execute(
                select(
                    Post.platform,
                    Post.content,
                    Post.comment_count,
                    Post.like_count,
                    Post.view_count,
                )
            ).all()
            jobs = session.execute(
                select(CrawlJob.status, Source.name).join(
                    Source,
                    Source.id == CrawlJob.source_id,
                )
            ).all()
        for platform, content, comments, likes, views in rows:
            entry = stats.setdefault(
                platform,
                {"platform": platform, "post_count": 0, "content_length": 0, "engagement": 0.0},
            )
            entry["post_count"] += 1
            entry["content_length"] += len(content or "")
            entry["engagement"] += self._engagement_score(likes, comments, views)
        job_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for status, source_name in jobs:
            platform = source_name.replace("demo-", "")
            job_counts[platform][status] += 1
        comparisons = []
        for platform, entry in sorted(stats.items()):
            count = entry["post_count"] or 1
            successful = job_counts[platform]["completed"] + job_counts[platform][
                "completed_with_warnings"
            ]
            total_jobs = sum(job_counts[platform].values())
            comparisons.append(
                {
                    "platform": platform,
                    "post_count": entry["post_count"],
                    "average_content_length": round(entry["content_length"] / count, 1),
                    "average_engagement_score": round(entry["engagement"] / count, 2),
                    "crawl_success_rate": round((successful / total_jobs) * 100, 1)
                    if total_jobs
                    else None,
                }
            )
        return {"platforms": comparisons}

    def analytics_data_quality(self) -> dict[str, Any]:
        """Return data quality and compliance diagnostics counts."""
        with get_session() as session:
            total_posts = int(session.execute(select(func.count(Post.id))).scalar() or 0)
            missing_title = int(
                session.execute(
                    select(func.count(Post.id)).where(or_(Post.title.is_(None), Post.title == ""))
                ).scalar()
                or 0
            )
            missing_content = int(
                session.execute(
                    select(func.count(Post.id)).where(
                        or_(Post.content.is_(None), Post.content == "")
                    )
                ).scalar()
                or 0
            )
            demo_records = int(
                session.execute(
                    select(func.count(Post.id)).where(Post.crawl_source == "demo")
                ).scalar()
                or 0
            )
            error_rows = session.execute(
                select(CrawlJob.error_category, func.count(CrawlJob.id))
                .where(CrawlJob.error_category.is_not(None))
                .group_by(CrawlJob.error_category)
            ).all()
        return {
            "total_posts": total_posts,
            "demo_records": demo_records,
            "checks": [
                {"name": "missing_title", "count": missing_title},
                {"name": "missing_content", "count": missing_content},
                {"name": "duplicate_content_hash", "count": self._duplicate_hash_count()},
                {"name": "demo_records", "count": demo_records},
            ],
            "policy_events": [
                {"category": category, "count": int(count)}
                for category, count in error_rows
                if category
            ],
        }

    def workflow_summary(self) -> dict[str, Any]:
        """Return a visual crawl workflow summary for the portfolio UI."""
        overview = self.analytics_overview()
        quality = self.analytics_data_quality()
        latest_error = next(
            (
                job
                for job in overview["latest_jobs"]
                if job.get("error_category") or job.get("status") == "failed"
            ),
            None,
        )
        stages = [
            ("source_select", "Source Select", "completed", overview["kpis"]["total_sources"]),
            (
                "policy_check",
                "Policy Check",
                "completed_with_warnings",
                len(quality["policy_events"]),
            ),
            ("robots_check", "Robots Check", "completed_with_warnings", 1),
            ("request_budget", "Request Budget", "completed", overview["kpis"]["total_crawl_runs"]),
            (
                "fetch_listing",
                "Fetch Listing",
                "completed",
                overview["kpis"]["successful_crawl_runs"],
            ),
            (
                "fetch_detail",
                "Fetch Detail",
                "completed_with_warnings",
                overview["kpis"]["failed_crawl_runs"],
            ),
            ("parse", "Parse HTML / JSON", "completed", overview["kpis"]["total_posts"]),
            ("normalize", "Normalize Schema", "completed", overview["kpis"]["total_posts"]),
            ("validate", "Validate Data", "completed_with_warnings", quality["checks"][1]["count"]),
            ("deduplicate", "Deduplicate", "completed", quality["checks"][2]["count"]),
            ("store", "Store SQLite", "completed", overview["kpis"]["total_posts"]),
            ("analyze_export", "Analyze / Export", "completed", len(self.list_reports())),
        ]
        return {
            "demo_dataset_present": overview["demo_dataset_present"],
            "latest_error": latest_error,
            "stages": [
                {
                    "key": key,
                    "label": label,
                    "status": status,
                    "count": count,
                    "error_reason": latest_error.get("error_reason")
                    if latest_error and key == "policy_check"
                    else None,
                }
                for key, label, status, count in stages
            ],
        }

    def _has_demo_dataset(self) -> bool:
        with get_session() as session:
            count = session.execute(
                select(func.count(Post.id)).where(Post.crawl_source == "demo")
            ).scalar()
            return bool(count)

    def _duplicate_hash_count(self, session=None) -> int:
        owns_session = session is None
        if owns_session:
            context = get_session()
            session = context.__enter__()
        try:
            rows = session.execute(
                select(Post.content_hash, func.count(Post.id))
                .where(Post.content_hash.is_not(None))
                .group_by(Post.content_hash)
                .having(func.count(Post.id) > 1)
            ).all()
            return int(sum(count - 1 for _, count in rows))
        finally:
            if owns_session:
                context.__exit__(None, None, None)

    def _keyword_counts(self, session, *, limit: int) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        rows = session.execute(select(Post.title, Post.excerpt, Post.content)).all()
        for title, excerpt, content in rows:
            text = normalize_text(" ".join([title or "", excerpt or "", content or ""]))
            for keyword in DEMO_KEYWORDS:
                count = text.count(normalize_text(keyword))
                if count:
                    counter[keyword] += count
        return [
            {"keyword": keyword, "count": count}
            for keyword, count in counter.most_common(limit)
        ]

    def _top_posts(self, session, *, limit: int) -> list[dict[str, Any]]:
        rows = session.execute(
            select(Post, Source.name).join(Source, Source.id == Post.source_id)
        ).all()
        scored = [self._post_engagement_dict(post, source_name) for post, source_name in rows]
        scored.sort(key=lambda item: item["engagement_score"], reverse=True)
        return scored[:limit]

    def _post_engagement_dict(self, post: Post, source_name: str) -> dict[str, Any]:
        return {
            "id": post.id,
            "source": source_name,
            "platform": post.platform,
            "board_or_forum": post.board_or_forum,
            "title": post.title,
            "published_at": post.published_at,
            "like_count": post.like_count or 0,
            "comment_count": post.comment_count or 0,
            "view_count": post.view_count or 0,
            "engagement_score": self._engagement_score(
                post.like_count,
                post.comment_count,
                post.view_count,
            ),
            "url": post.url,
        }

    def _job_dict(self, job: CrawlJob, source_name: str) -> dict[str, Any]:
        return {
            "id": job.id,
            "source": source_name,
            "job_type": job.job_type,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "error_category": job.error_category,
            "error_reason": job.error_reason,
            "request_count": job.request_count,
            "item_count": job.item_count,
        }

    @staticmethod
    def _date_key(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return value[:10] if len(value) >= 10 else None

    @staticmethod
    def _engagement_score(likes: int | None, comments: int | None, views: int | None) -> float:
        return round((comments or 0) * 2 + (likes or 0) + (views or 0) * 0.05, 2)


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
