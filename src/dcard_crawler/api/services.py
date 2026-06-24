"""Read/query and crawler-control services for the FastAPI backend."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
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
from dcard_crawler.services.source_catalog import load_source_catalog


class APIQueryService:
    """Query SQLite data for API responses."""

    def health(self) -> dict[str, Any]:
        """Return backend health and schema status."""
        return {"status": "ok", "database_ready": is_current_schema()}

    def list_sources(self) -> list[Source]:
        """Return all configured data sources."""
        with get_session() as session:
            return list(session.execute(select(Source).order_by(Source.name)).scalars().all())

    def source_catalog_status(self, catalog_path: str | None = None) -> list[dict[str, Any]]:
        """Return catalog entries merged with current SQLite status."""
        catalog = load_source_catalog(catalog_path)
        entries = catalog.entries
        with get_session() as session:
            source_rows = {
                source.name: source for source in session.execute(select(Source)).scalars().all()
            }
            post_counts = {
                source_name: int(count)
                for source_name, count in session.execute(
                    select(Source.name, func.count(Post.id))
                    .join(Post, Post.source_id == Source.id, isouter=True)
                    .group_by(Source.name)
                ).all()
            }
            latest_jobs: dict[str, CrawlJob] = {}
            for entry in entries:
                source = source_rows.get(entry.name)
                if not source:
                    continue
                latest = session.execute(
                    select(CrawlJob)
                    .where(CrawlJob.source_id == source.id)
                    .order_by(desc(CrawlJob.started_at))
                    .limit(1)
                ).scalar_one_or_none()
                if latest:
                    latest_jobs[entry.name] = latest

        response = []
        for entry in entries:
            source = source_rows.get(entry.name)
            latest = latest_jobs.get(entry.name)
            response.append(
                {
                    **entry.model_dump(),
                    "database_source_id": source.id if source else None,
                    "database_backed": source is not None,
                    "post_count": post_counts.get(entry.name, 0),
                    "latest_job": self._job_dict(latest, entry.name) if latest else None,
                    "last_status": latest.status if latest else None,
                    "last_error": latest.error_reason if latest else None,
                }
            )
        return response

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

    def search_posts(
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
    ) -> dict[str, Any]:
        """Return paginated posts with total count and simple facets."""
        with get_session() as session:
            base = select(Post, Source.name).join(Source, Source.id == Post.source_id)
            filters = []
            if platform:
                filters.append(Post.platform == platform)
            if source:
                filters.append(Source.name == source)
            if board_or_forum:
                filters.append(Post.board_or_forum == board_or_forum)
            if keyword:
                pattern = f"%{keyword}%"
                filters.append(
                    or_(
                        Post.title.ilike(pattern),
                        Post.excerpt.ilike(pattern),
                        Post.content.ilike(pattern),
                    )
                )
            if date_from:
                filters.append(or_(Post.published_at >= date_from, Post.created_at >= date_from))
            if date_to:
                filters.append(or_(Post.published_at <= date_to, Post.created_at <= date_to))
            for item in filters:
                base = base.where(item)

            count_query = select(func.count()).select_from(Post).join(Source)
            for item in filters:
                count_query = count_query.where(item)
            total = int(session.execute(count_query).scalar() or 0)
            rows = session.execute(
                base.order_by(desc(Post.crawled_at)).limit(limit).offset(offset)
            ).all()
            facets = {
                "platforms": [
                    {"value": name, "count": int(count)}
                    for name, count in session.execute(
                        select(Post.platform, func.count(Post.id)).group_by(Post.platform)
                    ).all()
                ],
                "sources": [
                    {"value": name, "count": int(count)}
                    for name, count in session.execute(
                        select(Source.name, func.count(Post.id))
                        .join(Post, Post.source_id == Source.id, isouter=True)
                        .group_by(Source.name)
                    ).all()
                ],
                "boards": [
                    {"value": name, "count": int(count)}
                    for name, count in session.execute(
                        select(Post.board_or_forum, func.count(Post.id))
                        .where(Post.board_or_forum.is_not(None))
                        .group_by(Post.board_or_forum)
                        .order_by(desc(func.count(Post.id)))
                        .limit(20)
                    ).all()
                ],
            }
        return {
            "rows": [self._post_response_dict(post, source_name) for post, source_name in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "facets": facets,
        }

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
            successful = (
                job_counts[platform]["completed"] + job_counts[platform]["completed_with_warnings"]
            )
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

    def analytics_dashboard(self) -> dict[str, Any]:
        """Return visualization-ready dashboard analytics."""
        overview = self.analytics_overview()
        trends = self.analytics_trends()
        quality = self.analytics_data_quality()
        return {
            "kpis": overview["kpis"],
            "daily_platform_volume": trends["daily_post_count"],
            "platform_distribution": overview["platforms"],
            "crawl_status_counts": self._crawl_status_counts(),
            "top_keywords": overview["top_keywords"],
            "top_posts": self.analytics_top_posts()["rows"][:10],
            "demo_live_ratio": self._demo_live_ratio(),
            "policy_events": quality["policy_events"],
        }

    def analytics_time_series(self) -> dict[str, Any]:
        """Return time-series data grouped for charts."""
        daily_platform: dict[tuple[str, str], int] = defaultdict(int)
        daily_source: dict[tuple[str, str], int] = defaultdict(int)
        daily_board: dict[tuple[str, str], int] = defaultdict(int)
        with get_session() as session:
            rows = session.execute(
                select(
                    Post.platform,
                    Source.name,
                    Post.board_or_forum,
                    Post.published_at,
                    Post.created_at,
                ).join(Source, Source.id == Post.source_id)
            ).all()
        for platform, source_name, board, published_at, created_at in rows:
            day = self._date_key(published_at or created_at)
            if not day:
                continue
            daily_platform[(day, platform)] += 1
            daily_source[(day, source_name)] += 1
            if board:
                daily_board[(day, board)] += 1
        return {
            "daily_by_platform": self._counter_points(daily_platform, "platform"),
            "daily_by_source": self._counter_points(daily_source, "source"),
            "daily_by_board": self._counter_points(daily_board, "board_or_forum"),
        }

    def analytics_keyword_network(self) -> dict[str, Any]:
        """Return keyword co-occurrence graph data."""
        keyword_counts: Counter[str] = Counter()
        link_counts: Counter[tuple[str, str]] = Counter()
        samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with get_session() as session:
            rows = session.execute(
                select(Post.id, Post.platform, Post.title, Post.excerpt, Post.content)
            ).all()
        for post_id, platform, title, excerpt, content in rows:
            text = normalize_text(" ".join([title or "", excerpt or "", content or ""]))
            matched = sorted({kw for kw in DEMO_KEYWORDS if normalize_text(kw) in text})
            for keyword in matched:
                keyword_counts[keyword] += 1
                if len(samples[keyword]) < 5:
                    samples[keyword].append(
                        {"post_id": post_id, "platform": platform, "title": title}
                    )
            for left, right in combinations(matched, 2):
                link_counts[(left, right)] += 1
        return {
            "nodes": [
                {
                    "id": keyword,
                    "label": keyword,
                    "value": count,
                    "samples": samples[keyword],
                    **self._keyword_category(keyword),
                    "metadata": {
                        "keyword": keyword,
                        "match_count": count,
                        "sample_count": len(samples[keyword]),
                    },
                }
                for keyword, count in keyword_counts.most_common(30)
            ],
            "links": [
                {"source": left, "target": right, "value": count}
                for (left, right), count in link_counts.most_common(60)
            ],
        }

    def analytics_compliance_summary(self) -> dict[str, Any]:
        """Return compliance and crawler governance dashboard data."""
        quality = self.analytics_data_quality()
        source_health = self.analytics_source_health()
        with get_session() as session:
            recent = session.execute(
                select(CrawlJob, Source.name)
                .join(Source)
                .order_by(desc(CrawlJob.started_at))
                .limit(20)
            ).all()
            status_rows = session.execute(
                select(CrawlJob.status, func.count(CrawlJob.id)).group_by(CrawlJob.status)
            ).all()
        policy_events = quality["policy_events"]
        return {
            "summary": {
                "policy_event_count": sum(item["count"] for item in policy_events),
                "blocked_count": sum(
                    item["count"]
                    for item in policy_events
                    if "403" in item["category"] or "blocked" in item["category"]
                ),
                "rate_limited_count": sum(
                    item["count"] for item in policy_events if "429" in item["category"]
                ),
                "source_count": len(source_health["rows"]),
            },
            "policy_events": policy_events,
            "status_counts": [
                {"status": status, "count": int(count)} for status, count in status_rows
            ],
            "source_health": source_health["rows"],
            "latest_diagnostics": [
                self._job_dict(job, source_name) for job, source_name in recent
            ],
            "governance_rules": [
                "Public data only",
                "robots.txt checked before fetch",
                "403/429/CAPTCHA/login wall fail closed",
                "Request budget and per-domain cooldown",
                "No CAPTCHA bypass, login bypass, or stealth evasion",
            ],
        }

    def analytics_keyword_heatmap(self) -> dict[str, Any]:
        """Return platform by keyword matrix."""
        platforms = sorted(self.platform_counts())
        keywords = DEMO_KEYWORDS
        matrix = {platform: dict.fromkeys(keywords, 0) for platform in platforms}
        with get_session() as session:
            rows = session.execute(
                select(Post.platform, Post.title, Post.excerpt, Post.content)
            ).all()
        for platform, title, excerpt, content in rows:
            text = normalize_text(" ".join([title or "", excerpt or "", content or ""]))
            for keyword in keywords:
                matrix.setdefault(platform, dict.fromkeys(keywords, 0))
                matrix[platform][keyword] += text.count(normalize_text(keyword))
        cells = [
            {"platform": platform, "keyword": keyword, "count": count}
            for platform, counts in matrix.items()
            for keyword, count in counts.items()
        ]
        return {"platforms": platforms, "keywords": keywords, "cells": cells}

    def analytics_source_health(self) -> dict[str, Any]:
        """Return source health matrix rows."""
        catalog = self.source_catalog_status()
        rows = []
        with get_session() as session:
            job_rows = session.execute(select(CrawlJob, Source.name).join(Source)).all()
        by_source: dict[str, list[CrawlJob]] = defaultdict(list)
        for job, source_name in job_rows:
            by_source[source_name].append(job)
        for entry in catalog:
            jobs = by_source.get(entry["name"], [])
            success = sum(
                1 for job in jobs if job.status in {"completed", "completed_with_warnings"}
            )
            failed = sum(1 for job in jobs if job.status == "failed")
            total = len(jobs)
            latest = max((job.started_at for job in jobs if job.started_at), default=None)
            rows.append(
                {
                    "source": entry["name"],
                    "display_name": entry["display_name"],
                    "platform": entry["platform"],
                    "enabled": entry["enabled"],
                    "post_count": entry["post_count"],
                    "success_rate": round((success / total) * 100, 1) if total else None,
                    "failed_count": failed,
                    "policy_events": sum(1 for job in jobs if job.error_category),
                    "freshness": latest.isoformat() if latest else None,
                    "last_status": entry["last_status"],
                    "last_error": entry["last_error"],
                }
            )
        return {"rows": rows}

    def analytics_lineage(self) -> dict[str, Any]:
        """Return a compact lineage graph."""
        nodes = [
            {"id": "sources", "label": "Sources", "type": "source"},
            {"id": "crawl_jobs", "label": "Crawl Jobs", "type": "job"},
            {"id": "raw_records", "label": "Raw Records", "type": "raw"},
            {"id": "posts", "label": "Normalized Posts", "type": "post"},
            {"id": "keyword_matches", "label": "Keyword Matches", "type": "analysis"},
            {"id": "reports", "label": "Reports", "type": "report"},
        ]
        counts = self.counts()
        nodes[0]["count"] = counts["sources"]
        nodes[1]["count"] = counts["crawl_jobs"]
        nodes[2]["count"] = counts["posts"]
        nodes[3]["count"] = counts["posts"]
        nodes[4]["count"] = sum(item["count"] for item in self.analytics_keywords()["keywords"])
        nodes[5]["count"] = len(self.list_reports())
        return {
            "nodes": nodes,
            "edges": [
                {"source": "sources", "target": "crawl_jobs", "label": "starts"},
                {"source": "crawl_jobs", "target": "raw_records", "label": "fetches"},
                {"source": "raw_records", "target": "posts", "label": "normalizes"},
                {"source": "posts", "target": "keyword_matches", "label": "analyzes"},
                {"source": "keyword_matches", "target": "reports", "label": "exports"},
            ],
        }

    def analytics_crawl_flow(self) -> dict[str, Any]:
        """Return React Flow-ready crawl pipeline data."""
        workflow = self.workflow_summary()
        x_gap = 210
        nodes = []
        for index, stage in enumerate(workflow["stages"]):
            detail = self._workflow_stage_detail(stage["key"])
            nodes.append(
                {
                    "id": stage["key"],
                    "type": "default",
                    "position": {"x": (index % 4) * x_gap, "y": (index // 4) * 150},
                    "data": {
                        "label": stage["label"],
                        "status": stage["status"],
                        "count": stage["count"],
                        "purpose": detail["purpose"],
                        "inputs": detail["inputs"],
                        "outputs": detail["outputs"],
                        "tables": detail["tables"],
                        "failure_modes": detail["failure_modes"],
                        "compliance": detail["compliance"],
                        "request_count": self.counts()["crawl_jobs"] if index < 4 else 0,
                        "item_count": stage["count"],
                        "failed_count": workflow["latest_error"] is not None,
                        "latest_error": stage.get("error_reason"),
                        "output_artifact": detail["artifact"],
                    },
                }
            )
        edges = [
            {
                "id": f"{workflow['stages'][index]['key']}-{workflow['stages'][index + 1]['key']}",
                "source": workflow["stages"][index]["key"],
                "target": workflow["stages"][index + 1]["key"],
                "animated": index < 5,
            }
            for index in range(len(workflow["stages"]) - 1)
        ]
        return {"nodes": nodes, "edges": edges}

    def analytics_demo_story(self) -> dict[str, Any]:
        """Return interview-demo story data for visual operation guides."""
        overview = self.analytics_overview()
        dashboard = self.analytics_dashboard()
        workflow = self.workflow_summary()
        steps = []
        for index, stage in enumerate(workflow["stages"], start=1):
            detail = self._workflow_stage_detail(stage["key"])
            steps.append(
                {
                    "index": index,
                    "key": stage["key"],
                    "label": stage["label"],
                    "status": stage["status"],
                    "count": stage["count"],
                    "purpose": detail["purpose"],
                    "inputs": detail["inputs"],
                    "outputs": detail["outputs"],
                    "tables": detail["tables"],
                    "artifact": detail["artifact"],
                    "failure_modes": detail["failure_modes"],
                    "compliance": detail["compliance"],
                    "engineering_highlight": detail["engineering_highlight"],
                }
            )
        return {
            "title": "Taiwan Public Web Intelligence Workbench",
            "subtitle": "Public-data crawler governance, analytics, and Excel reporting.",
            "demo_dataset_present": overview["demo_dataset_present"],
            "kpis": overview["kpis"],
            "demo_live_ratio": dashboard["demo_live_ratio"],
            "walkthrough_steps": steps,
            "architecture": self._architecture_graph(),
            "lifecycle": self._lifecycle_graph(),
            "interview_highlights": [
                "Public-source governance runs before crawler requests.",
                "Connectors normalize forums, RSS/news, and APIs into one schema.",
                "SQLite lineage links jobs, posts, quality checks, analytics, and exports.",
                "Fail-closed compliance records 403, 429, CAPTCHA, login, and robots events.",
                "Excel/CSV/SQLite analytics make the project useful beyond crawling.",
            ],
        }

    def analytics_top_posts(self) -> dict[str, Any]:
        """Return top post table rows."""
        with get_session() as session:
            rows = self._top_posts(session, limit=100)
        return {"rows": rows}

    def analytics_data_quality_table(self) -> dict[str, Any]:
        """Return data quality tables for UI."""
        with get_session() as session:
            missing = session.execute(
                select(Post, Source.name)
                .join(Source)
                .where(or_(Post.content.is_(None), Post.content == ""))
                .limit(100)
            ).all()
            duplicate_hashes = session.execute(
                select(Post.content_hash, func.count(Post.id))
                .where(Post.content_hash.is_not(None))
                .group_by(Post.content_hash)
                .having(func.count(Post.id) > 1)
            ).all()
            failed = session.execute(
                select(CrawlJob, Source.name)
                .join(Source)
                .where(CrawlJob.status == "failed")
                .order_by(desc(CrawlJob.started_at))
                .limit(100)
            ).all()
            policy = session.execute(
                select(CrawlJob, Source.name)
                .join(Source)
                .where(CrawlJob.error_category.is_not(None))
                .order_by(desc(CrawlJob.started_at))
                .limit(100)
            ).all()
        return {
            "missing_content": [
                self._quality_post_row(post, source_name) for post, source_name in missing
            ],
            "duplicates": [
                {"content_hash": content_hash, "duplicate_count": int(count)}
                for content_hash, count in duplicate_hashes
            ],
            "failed_crawls": [self._job_dict(job, source_name) for job, source_name in failed],
            "policy_blocks": [self._job_dict(job, source_name) for job, source_name in policy],
        }

    def analytics_drilldown(self, *, kind: str, item_id: str) -> dict[str, Any]:
        """Return a unified drawer payload for UI drilldown."""
        if kind == "report":
            reports = self.list_reports()
            report = next((item for item in reports if item["path"] == item_id), None)
            if not report:
                return self._empty_drilldown(kind, item_id)
            return {
                "kind": kind,
                "id": item_id,
                "title": Path(item_id).name,
                "subtitle": report.get("report_type") or "report",
                "summary": {
                    "status": report.get("status"),
                    "platform": report.get("platform"),
                    "generated_at": report.get("generated_at"),
                },
                "metadata": report,
                "related_posts": self.search_posts(limit=8)["rows"],
                "related_jobs": self.analytics_overview()["latest_jobs"],
                "quality_flags": [],
                "raw_payload": report,
            }
        if kind == "quality":
            quality = self.analytics_data_quality()
            return {
                "kind": kind,
                "id": item_id,
                "title": item_id.replace("_", " ").title(),
                "subtitle": "Data quality drilldown",
                "summary": quality,
                "metadata": {
                    "quality_key": item_id,
                    "checks": quality["checks"],
                    "policy_events": quality["policy_events"],
                },
                "related_posts": self.search_posts(limit=8)["rows"],
                "related_jobs": self.analytics_overview()["latest_jobs"],
                "quality_flags": [item_id],
                "raw_payload": quality,
            }
        with get_session() as session:
            if kind == "post":
                post = session.get(Post, int(item_id))
                if not post:
                    return self._empty_drilldown(kind, item_id)
                source = session.get(Source, post.source_id)
                source_name = source.name if source else "unknown"
                return {
                    "kind": kind,
                    "id": item_id,
                    "title": post.title,
                    "subtitle": f"{post.platform} / {post.board_or_forum or '-'}",
                    "summary": {
                        "engagement_score": self._engagement_score(
                            post.like_count,
                            post.comment_count,
                            post.view_count,
                        ),
                        "content_length": len(post.content or ""),
                        "crawl_source": post.crawl_source,
                    },
                    "metadata": self._post_response_dict(post, source_name),
                    "related_posts": self._related_posts(
                        session,
                        post.platform,
                        post.board_or_forum,
                    ),
                    "related_jobs": self._related_jobs(session, post.source_id),
                    "quality_flags": self._post_quality_flags(post),
                    "raw_payload": post.raw_json or {},
                }
            if kind == "source":
                source = session.execute(
                    select(Source).where(Source.name == item_id)
                ).scalar_one_or_none()
                if not source and item_id.isdigit():
                    source = session.get(Source, int(item_id))
                if not source:
                    return self._empty_drilldown(kind, item_id)
                post_count = int(
                    session.execute(
                        select(func.count(Post.id)).where(Post.source_id == source.id)
                    ).scalar()
                    or 0
                )
                return {
                    "kind": kind,
                    "id": str(source.id),
                    "title": source.name,
                    "subtitle": source.source_type,
                    "summary": {"post_count": post_count, "enabled": source.enabled},
                    "metadata": {
                        "base_url": source.base_url,
                        "robots_url": source.robots_url,
                        "notes": source.notes,
                    },
                    "related_posts": self._related_posts(session, None, None, source_id=source.id),
                    "related_jobs": self._related_jobs(session, source.id),
                    "quality_flags": [],
                    "raw_payload": {},
                }
            if kind == "job":
                job = session.get(CrawlJob, int(item_id))
                if not job:
                    return self._empty_drilldown(kind, item_id)
                source = session.get(Source, job.source_id)
                return {
                    "kind": kind,
                    "id": item_id,
                    "title": f"{source.name if source else 'unknown'} / {job.job_type}",
                    "subtitle": job.status,
                    "summary": {
                        "request_count": job.request_count,
                        "item_count": job.item_count,
                        "error_category": job.error_category,
                    },
                    "metadata": self._job_dict(job, source.name if source else "unknown"),
                    "related_posts": self._related_posts(
                        session,
                        None,
                        None,
                        source_id=job.source_id,
                    ),
                    "related_jobs": [self._job_dict(job, source.name if source else "unknown")],
                    "quality_flags": [job.error_reason] if job.error_reason else [],
                    "raw_payload": {"error_message": job.error_message},
                }
        if kind == "keyword":
            return self._keyword_drilldown(item_id)
        if kind == "platform":
            return self._platform_drilldown(item_id)
        if kind == "workflow_node":
            try:
                detail = self._workflow_stage_detail(item_id)
            except KeyError:
                return {
                    "kind": kind,
                    "id": item_id,
                    "title": item_id.replace("_", " ").title(),
                    "subtitle": "Graph node",
                    "summary": {"node_type": "visualization"},
                    "metadata": {"id": item_id},
                    "related_posts": self.search_posts(limit=8)["rows"],
                    "related_jobs": self.analytics_overview()["latest_jobs"],
                    "quality_flags": [],
                    "raw_payload": {},
                }
            return {
                "kind": kind,
                "id": item_id,
                "title": item_id.replace("_", " ").title(),
                "subtitle": detail["purpose"],
                "summary": {"artifact": detail["artifact"], "compliance": detail["compliance"]},
                "metadata": detail,
                "related_posts": self.search_posts(limit=8)["rows"],
                "related_jobs": [item for item, _ in []],
                "quality_flags": detail["failure_modes"],
                "raw_payload": detail,
            }
        if kind == "kpi":
            overview = self.analytics_overview()
            return {
                "kind": kind,
                "id": item_id,
                "title": item_id.replace("_", " ").title(),
                "subtitle": "Dashboard KPI",
                "summary": overview["kpis"],
                "metadata": {
                    "demo_dataset_present": overview["demo_dataset_present"],
                    "platforms": overview["platforms"],
                },
                "related_posts": overview["top_posts"],
                "related_jobs": overview["latest_jobs"],
                "quality_flags": [],
                "raw_payload": overview,
            }
        return self._empty_drilldown(kind, item_id)

    def finalize_drilldown(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ensure drilldown payloads always expose metadata diagnostics."""
        metadata = payload.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {"value": metadata}
        available = sorted(str(key) for key, value in metadata.items() if value not in (None, ""))
        missing = sorted(str(key) for key, value in metadata.items() if value in (None, ""))
        if not available:
            metadata = {
                "kind": payload.get("kind"),
                "id": payload.get("id"),
                "metadata_note": "No source-specific metadata was available.",
            }
            available = sorted(metadata)
        payload["metadata"] = metadata
        payload["metadata_status"] = "available" if available else "missing"
        payload["available_fields"] = available
        payload["missing_fields"] = missing
        return payload

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

    @staticmethod
    def _workflow_stage_detail(key: str) -> dict[str, Any]:
        details = {
            "source_select": {
                "purpose": "Choose a public, cataloged source before any network request.",
                "inputs": ["configs/sources.yaml", "sources table", "enabled source filters"],
                "outputs": ["connector target", "source_id", "crawl job intent"],
                "tables": ["sources"],
                "artifact": "selected source catalog entry",
                "failure_modes": [
                    "source disabled",
                    "missing catalog entry",
                    "unsupported connector",
                ],
                "compliance": "Only configured public sources are eligible for crawling.",
                "engineering_highlight": "Source registry separates intent from connector code.",
            },
            "policy_check": {
                "purpose": "Evaluate platform policy, stop conditions, budget, and source health.",
                "inputs": ["crawler policy settings", "source metadata", "latest crawl jobs"],
                "outputs": ["allow / slow down / fail-closed decision", "error_category"],
                "tables": ["crawl_jobs"],
                "artifact": "policy decision in crawl job diagnostics",
                "failure_modes": [
                    "http_403_forbidden",
                    "http_429_rate_limited",
                    "captcha_detected",
                    "login_required",
                ],
                "compliance": "The crawler records blocks and stops; it never attempts bypass.",
                "engineering_highlight": "Anti-bot handling is diagnostic and conservative.",
            },
            "robots_check": {
                "purpose": "Check robots.txt and domain rules before fetching public pages.",
                "inputs": ["robots_url", "target_url", "user agent policy"],
                "outputs": ["robots allowed/disallowed/unavailable status"],
                "tables": ["crawl_jobs"],
                "artifact": "robots decision in structured logs",
                "failure_modes": ["robots_disallowed", "robots_unavailable"],
                "compliance": "Robots disallow fails closed; unavailable robots needs policy.",
                "engineering_highlight": "Robots handling is centralized in crawler core.",
            },
            "request_budget": {
                "purpose": "Limit request volume per job and cool down domains after rate limits.",
                "inputs": ["request_budget_per_job", "per-domain rate limiter", "cooldown config"],
                "outputs": ["remaining budget", "cooldown state", "request_count"],
                "tables": ["crawl_jobs"],
                "artifact": "request counters and domain cooldown logs",
                "failure_modes": ["request_budget_exceeded", "domain_cooldown_active"],
                "compliance": "Small, polite crawl budgets reduce server pressure.",
                "engineering_highlight": "Budgeting makes live verification safe and repeatable.",
            },
            "fetch_listing": {
                "purpose": "Fetch listing, RSS, sitemap, or API index data through connectors.",
                "inputs": ["connector target", "http client", "rate limiter"],
                "outputs": ["raw listing payload", "candidate item URLs/IDs"],
                "tables": ["crawl_jobs"],
                "artifact": "listing response metadata",
                "failure_modes": ["empty listing", "parser mismatch", "network timeout"],
                "compliance": "Uses public endpoints/pages and honors fail-closed policy errors.",
                "engineering_highlight": "API-first and RSS/sitemap-first reduce brittle scraping.",
            },
            "fetch_detail": {
                "purpose": "Fetch public detail pages or API detail payloads for selected items.",
                "inputs": ["candidate items", "max_posts", "checkpoint state"],
                "outputs": ["raw detail JSON/HTML", "detail fetch provenance"],
                "tables": ["crawl_jobs"],
                "artifact": "detail response metadata",
                "failure_modes": ["detail blocked", "not found", "login wall"],
                "compliance": "Blocked detail pages are recorded and skipped; no bypass.",
                "engineering_highlight": "Checkpoint-friendly detail fetches support resume.",
            },
            "parse": {
                "purpose": "Parse JSON, RSS XML, or HTML into intermediate records.",
                "inputs": ["raw payload", "connector parser", "html/text utilities"],
                "outputs": ["parsed title/content/metadata fields"],
                "tables": ["crawl_jobs"],
                "artifact": "parser diagnostics and skipped item reasons",
                "failure_modes": ["missing title", "missing content", "invalid date"],
                "compliance": "Parser handles only captured public content and metadata.",
                "engineering_highlight": "Parsing is connector-specific; contracts stay shared.",
            },
            "normalize": {
                "purpose": "Convert platform records into the NormalizedPost schema.",
                "inputs": ["parsed item", "source_id", "platform metadata"],
                "outputs": ["NormalizedPost", "content_hash", "canonical fields"],
                "tables": ["posts"],
                "artifact": "normalized post payload",
                "failure_modes": [
                    "invalid schema",
                    "missing external_id",
                    "unsupported platform field",
                ],
                "compliance": "Normalization excludes credentials, cookies, and non-public data.",
                "engineering_highlight": "One schema powers analysis and Excel export.",
            },
            "validate": {
                "purpose": "Check completeness, timestamps, content length, and quality flags.",
                "inputs": ["NormalizedPost", "quality rules"],
                "outputs": ["quality counters", "warnings", "accepted/skipped decision"],
                "tables": ["posts", "crawl_jobs"],
                "artifact": "data quality table rows",
                "failure_modes": ["empty content", "invalid date", "malformed URL"],
                "compliance": "Quality warnings are visible instead of hidden in logs.",
                "engineering_highlight": "Data quality becomes visible UI output, not silent logs.",
            },
            "deduplicate": {
                "purpose": "Use source/external ID and content hash to avoid duplicate records.",
                "inputs": ["source_id", "external_id", "content_hash"],
                "outputs": ["insert/update decision", "duplicate counters"],
                "tables": ["posts"],
                "artifact": "upsert result",
                "failure_modes": ["duplicate hash", "conflicting external_id"],
                "compliance": "Deduplication reduces unnecessary repeated processing.",
                "engineering_highlight": "Upsert behavior keeps repeated crawls idempotent.",
            },
            "store": {
                "purpose": "Persist sources, jobs, normalized posts, metrics, and report metadata.",
                "inputs": ["NormalizedPost", "crawl job lifecycle", "metrics"],
                "outputs": ["SQLite rows", "queryable analytics dataset"],
                "tables": ["sources", "crawl_jobs", "posts", "post_metrics"],
                "artifact": "SQLite database",
                "failure_modes": ["schema mismatch", "database write error"],
                "compliance": "Stored provenance keeps public-source origin visible.",
                "engineering_highlight": "SQLite keeps local data with clear lineage.",
            },
            "analyze_export": {
                "purpose": "Aggregate trends, keywords, engagement, health, and Excel sheets.",
                "inputs": ["SQLite posts", "crawl jobs", "keyword dictionary"],
                "outputs": ["charts", "analytics API payloads", "Excel/CSV/JSON reports"],
                "tables": ["posts", "crawl_jobs", "exports"],
                "artifact": "Excel report / analytics dashboard",
                "failure_modes": ["empty dataset", "missing metrics", "export path unavailable"],
                "compliance": "Reports label demo data and keep blocked crawl reasons visible.",
                "engineering_highlight": "The crawler feeds analysis, not just raw collection.",
            },
        }
        return details[key]

    @staticmethod
    def _architecture_graph() -> dict[str, Any]:
        nodes = [
            {
                "id": "sources",
                "label": "Public Sources",
                "type": "source",
                "position": {"x": 0, "y": 80},
            },
            {
                "id": "connectors",
                "label": "Connectors",
                "type": "connector",
                "position": {"x": 220, "y": 80},
            },
            {
                "id": "core",
                "label": "Crawler Core",
                "type": "core",
                "position": {"x": 440, "y": 80},
            },
            {
                "id": "sqlite",
                "label": "SQLite Store",
                "type": "database",
                "position": {"x": 660, "y": 80},
            },
            {
                "id": "analytics",
                "label": "Analytics API",
                "type": "api",
                "position": {"x": 880, "y": 20},
            },
            {
                "id": "react",
                "label": "React Dashboard",
                "type": "ui",
                "position": {"x": 1100, "y": 20},
            },
            {
                "id": "excel",
                "label": "Excel Export",
                "type": "export",
                "position": {"x": 1100, "y": 150},
            },
        ]
        edges = [
            {"source": "sources", "target": "connectors", "label": "select target"},
            {"source": "connectors", "target": "core", "label": "fetch/parse contract"},
            {"source": "core", "target": "sqlite", "label": "normalize/store"},
            {"source": "sqlite", "target": "analytics", "label": "query"},
            {"source": "analytics", "target": "react", "label": "visualize"},
            {"source": "sqlite", "target": "excel", "label": "export"},
        ]
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _lifecycle_graph() -> dict[str, Any]:
        nodes = [
            {"id": "raw", "label": "Raw Response", "type": "raw", "position": {"x": 0, "y": 80}},
            {
                "id": "parsed",
                "label": "Parsed Item",
                "type": "parse",
                "position": {"x": 190, "y": 80},
            },
            {
                "id": "post",
                "label": "Normalized Post",
                "type": "post",
                "position": {"x": 380, "y": 80},
            },
            {
                "id": "hash",
                "label": "Dedupe Hash",
                "type": "quality",
                "position": {"x": 570, "y": 20},
            },
            {
                "id": "keyword",
                "label": "Keyword Match",
                "type": "analysis",
                "position": {"x": 570, "y": 140},
            },
            {
                "id": "chart",
                "label": "Analytics Chart",
                "type": "analysis",
                "position": {"x": 760, "y": 80},
            },
            {
                "id": "excel",
                "label": "Excel Sheet",
                "type": "export",
                "position": {"x": 950, "y": 80},
            },
        ]
        edges = [
            {"source": "raw", "target": "parsed", "label": "parse"},
            {"source": "parsed", "target": "post", "label": "normalize"},
            {"source": "post", "target": "hash", "label": "dedupe"},
            {"source": "post", "target": "keyword", "label": "analyze text"},
            {"source": "keyword", "target": "chart", "label": "aggregate"},
            {"source": "hash", "target": "chart", "label": "quality flags"},
            {"source": "chart", "target": "excel", "label": "export"},
        ]
        return {"nodes": nodes, "edges": edges}

    def _crawl_status_counts(self) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.execute(
                select(CrawlJob.status, func.count(CrawlJob.id)).group_by(CrawlJob.status)
            ).all()
        return [{"status": status, "count": int(count)} for status, count in rows]

    def _demo_live_ratio(self) -> dict[str, int]:
        with get_session() as session:
            demo = int(
                session.execute(
                    select(func.count(Post.id)).where(Post.crawl_source == "demo")
                ).scalar()
                or 0
            )
            total = int(session.execute(select(func.count(Post.id))).scalar() or 0)
        return {"demo": demo, "live": max(total - demo, 0), "total": total}

    @staticmethod
    def _counter_points(
        counter: dict[tuple[str, str], int],
        group_key: str,
    ) -> list[dict[str, Any]]:
        return [
            {"date": day, group_key: group, "count": count}
            for (day, group), count in sorted(counter.items())
        ]

    def _post_response_dict(self, post: Post, source_name: str) -> dict[str, Any]:
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
            "crawled_at": post.crawled_at.isoformat() if post.crawled_at else None,
            "like_count": post.like_count or 0,
            "comment_count": post.comment_count or 0,
            "share_count": post.share_count or 0,
            "view_count": post.view_count or 0,
            "url": post.url,
            "canonical_url": post.canonical_url,
            "content_hash": post.content_hash,
        }

    def _related_posts(
        self,
        session,
        platform: str | None,
        board_or_forum: str | None,
        *,
        source_id: int | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        query = select(Post, Source.name).join(Source, Source.id == Post.source_id)
        if source_id:
            query = query.where(Post.source_id == source_id)
        elif platform:
            query = query.where(Post.platform == platform)
            if board_or_forum:
                query = query.where(Post.board_or_forum == board_or_forum)
        rows = session.execute(query.order_by(desc(Post.crawled_at)).limit(limit)).all()
        return [self._post_response_dict(post, source_name) for post, source_name in rows]

    def _related_jobs(self, session, source_id: int, *, limit: int = 8) -> list[dict[str, Any]]:
        rows = session.execute(
            select(CrawlJob, Source.name)
            .join(Source)
            .where(CrawlJob.source_id == source_id)
            .order_by(desc(CrawlJob.started_at))
            .limit(limit)
        ).all()
        return [self._job_dict(job, source_name) for job, source_name in rows]

    @staticmethod
    def _post_quality_flags(post: Post) -> list[str]:
        flags = []
        if not post.content:
            flags.append("missing_content")
        if not post.published_at:
            flags.append("missing_published_at")
        if not post.content_hash:
            flags.append("missing_content_hash")
        if post.crawl_source == "demo":
            flags.append("demo_dataset")
        return flags

    def _keyword_drilldown(self, keyword: str) -> dict[str, Any]:
        rows = self.search_posts(keyword=keyword, limit=12)["rows"]
        category = self._keyword_category(keyword)
        return {
            "kind": "keyword",
            "id": keyword,
            "title": keyword,
            "subtitle": "Keyword drilldown",
            "summary": {"related_posts": len(rows)},
            "metadata": {
                "keyword": keyword,
                **category,
                "heatmap_cells": [
                    cell
                    for cell in self.analytics_keyword_heatmap()["cells"]
                    if cell["keyword"] == keyword
                ],
            },
            "related_posts": rows,
            "related_jobs": self.analytics_overview()["latest_jobs"],
            "quality_flags": [],
            "raw_payload": self.analytics_keyword_network(),
        }

    def _platform_drilldown(self, platform: str) -> dict[str, Any]:
        rows = self.search_posts(platform=platform, limit=12)["rows"]
        stats = next(
            (
                item
                for item in self.analytics_platforms()["platforms"]
                if item["platform"] == platform
            ),
            {},
        )
        return {
            "kind": "platform",
            "id": platform,
            "title": platform,
            "subtitle": "Platform drilldown",
            "summary": stats,
            "metadata": {
                "source_health": [
                    row
                    for row in self.analytics_source_health()["rows"]
                    if row["platform"] == platform
                ],
            },
            "related_posts": rows,
            "related_jobs": self.analytics_overview()["latest_jobs"],
            "quality_flags": [],
            "raw_payload": stats,
        }

    @staticmethod
    def _empty_drilldown(kind: str, item_id: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "id": item_id,
            "title": f"{kind}:{item_id}",
            "subtitle": "No matching record found.",
            "summary": {},
            "metadata": {},
            "related_posts": [],
            "related_jobs": [],
            "quality_flags": ["not_found"],
            "raw_payload": {},
        }

    @staticmethod
    def _keyword_category(keyword: str) -> dict[str, str]:
        tech = {"AI", "生成式AI", "Python", "半導體"}
        finance = {"台積電"}
        career = {"工作", "面試", "薪資"}
        analysis = {"資料分析"}
        work_style = {"遠端工作"}
        if keyword in tech:
            return {"category": "tech-ai", "group": "AI / Tech", "color": "#2563eb"}
        if keyword in finance:
            return {"category": "finance", "group": "Finance", "color": "#0f766e"}
        if keyword in career:
            return {"category": "career", "group": "Career", "color": "#f59e0b"}
        if keyword in analysis:
            return {"category": "data-analysis", "group": "Data Analysis", "color": "#7c3aed"}
        if keyword in work_style:
            return {"category": "work-style", "group": "Work Style", "color": "#0891b2"}
        return {"category": "topic", "group": "Topic", "color": "#64748b"}

    @staticmethod
    def _quality_post_row(post: Post, source_name: str) -> dict[str, Any]:
        return {
            "id": post.id,
            "source": source_name,
            "platform": post.platform,
            "external_id": post.external_id,
            "title": post.title,
            "board_or_forum": post.board_or_forum,
            "published_at": post.published_at,
            "url": post.url,
            "content_hash": post.content_hash,
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
            {"keyword": keyword, "count": count} for keyword, count in counter.most_common(limit)
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

    def run_demo_workflow(self, *, rows: int = 2000, reset_demo: bool = True) -> dict[str, Any]:
        """Seed demo data for the interactive portfolio walkthrough."""
        from dcard_crawler.services.demo_seed import DemoSeedService

        return DemoSeedService().seed(rows=rows, reset_demo=reset_demo)

    def generate_excel_report(
        self,
        *,
        output_path: str = "data/exports/analysis_report.xlsx",
    ) -> dict[str, Any]:
        """Generate the portfolio Excel report through the analysis pipeline."""
        from dcard_crawler.analysis.excel_report import export_analysis_report

        tables = export_analysis_report(None, output_path, "configs/keywords.txt", None)
        path = Path(output_path)
        return {
            "status": "completed",
            "output_path": str(path),
            "row_count": int(len(tables.get("Raw Data", []))),
            "keyword_match_count": int(len(tables.get("Keyword Matches", []))),
            "sheets": list(tables),
        }
