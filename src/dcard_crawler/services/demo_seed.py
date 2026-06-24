"""Generate portfolio demo data through the normal repository path."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from dcard_crawler.analysis.topic_taxonomy import TOPIC_TAXONOMY, TopicDefinition
from dcard_crawler.core.text_utils import content_hash
from dcard_crawler.database import get_session, init_db
from dcard_crawler.models import CrawlJob, Post, Source
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost

DEMO_KEYWORDS = [keyword.keyword for topic in TOPIC_TAXONOMY for keyword in topic.keywords]


@dataclass(frozen=True)
class DemoSourceSpec:
    name: str
    platform: str
    source_type: str
    base_url: str
    robots_url: str | None
    boards: tuple[str, ...]


DEMO_SOURCES = (
    DemoSourceSpec(
        name="demo-ptt",
        platform="ptt",
        source_type="forum",
        base_url="https://www.ptt.cc",
        robots_url="https://www.ptt.cc/robots.txt",
        boards=("Stock", "Tech_Job", "Soft_Job", "NBA"),
    ),
    DemoSourceSpec(
        name="demo-dcard",
        platform="dcard",
        source_type="forum",
        base_url="https://www.dcard.tw",
        robots_url="https://www.dcard.tw/robots.txt",
        boards=("trending", "job", "tech", "finance"),
    ),
    DemoSourceSpec(
        name="demo-news",
        platform="news",
        source_type="news",
        base_url="https://news.example.com",
        robots_url="https://news.example.com/robots.txt",
        boards=("科技", "財經", "生活", "產業"),
    ),
)


class DemoSeedService:
    """Seed a realistic, clearly labeled portfolio preview dataset."""

    def __init__(
        self,
        *,
        source_repository: SourceRepository | None = None,
        post_repository: PostRepository | None = None,
        crawl_job_repository: CrawlJobRepository | None = None,
        report_root: str | Path = "data/reports",
        seed: int = 42,
    ) -> None:
        self.source_repository = source_repository or SourceRepository()
        self.post_repository = post_repository or PostRepository(self.source_repository)
        self.crawl_job_repository = crawl_job_repository or CrawlJobRepository()
        self.report_root = Path(report_root)
        self.random = random.Random(seed)

    def seed(self, *, rows: int = 2000, reset_demo: bool = False) -> dict[str, Any]:
        """Seed demo sources, posts, crawl jobs, and JSON report summaries."""
        init_db(reset=False)
        if reset_demo:
            self.reset_demo_data()

        source_ids = self._ensure_sources()
        inserted = 0
        updated = 0
        for index in range(rows):
            spec = DEMO_SOURCES[index % len(DEMO_SOURCES)]
            normalized = self._build_post(index=index, spec=spec, source_id=source_ids[spec.name])
            if self.post_repository.upsert(normalized):
                inserted += 1
            else:
                updated += 1

        jobs = self._seed_jobs(source_ids)
        reports = self._write_reports(rows=rows, jobs=jobs)
        return {
            "demo": True,
            "rows_requested": rows,
            "posts_inserted": inserted,
            "posts_updated": updated,
            "sources": len(source_ids),
            "crawl_jobs": len(jobs),
            "reports": reports,
        }

    def reset_demo_data(self) -> None:
        """Delete only records that belong to the generated demo dataset."""
        demo_names = [spec.name for spec in DEMO_SOURCES]
        with get_session() as session:
            source_ids = list(
                session.execute(select(Source.id).where(Source.name.in_(demo_names))).scalars()
            )
            if source_ids:
                session.execute(delete(CrawlJob).where(CrawlJob.source_id.in_(source_ids)))
                session.execute(delete(Post).where(Post.source_id.in_(source_ids)))
            session.execute(delete(Post).where(Post.crawl_source == "demo"))

    def _ensure_sources(self) -> dict[str, int]:
        source_ids: dict[str, int] = {}
        for spec in DEMO_SOURCES:
            source_ids[spec.name] = self.source_repository.get_or_create(
                name=spec.name,
                source_type=spec.source_type,
                base_url=spec.base_url,
                robots_url=spec.robots_url,
                notes=(
                    "Demo dataset generated for portfolio preview; "
                    "not collected from live sites."
                ),
            )
        return source_ids

    def _build_post(self, *, index: int, spec: DemoSourceSpec, source_id: int) -> NormalizedPost:
        primary_topic = self.random.choice(TOPIC_TAXONOMY)
        secondary_topic = self.random.choice(
            [topic for topic in TOPIC_TAXONOMY if topic.topic_id != primary_topic.topic_id]
        )
        primary_keywords = self.random.sample(
            list(primary_topic.keywords),
            k=min(3, len(primary_topic.keywords)),
        )
        secondary_keyword = self.random.choice(secondary_topic.keywords)
        keywords = [item.keyword for item in primary_keywords] + [secondary_keyword.keyword]
        keyword = keywords[0]
        board = self.random.choice(spec.boards)
        days_ago = self.random.randint(0, 44)
        minutes = self.random.randint(0, 24 * 60)
        published_at = (datetime.now() - timedelta(days=days_ago, minutes=minutes)).replace(
            microsecond=0
        )
        external_id = f"demo-{spec.platform}-{index:05d}"
        quality_case = "ok"
        content = self._topic_content(
            primary_topic=primary_topic,
            secondary_topic=secondary_topic,
            keywords=keywords,
            board=board,
            platform=spec.platform,
        )
        if index % 37 == 0:
            content = ""
            quality_case = "missing_content"

        title = (
            f"{primary_topic.topic_name} 趨勢觀察："
            f"{keyword} 與 {secondary_keyword.keyword} 樣本 {index + 1}"
        )
        if index % 113 == 0:
            title = f"{keyword} 快訊：{primary_topic.topic_name} 討論升溫"

        base_url = spec.base_url.rstrip("/")
        url = f"{base_url}/demo/{board}/{external_id}"
        like_count = self._metric_value(spec.platform, "like")
        comment_count = self._metric_value(spec.platform, "comment")
        view_count = self._metric_value(spec.platform, "view")
        raw_json = {
            "demo": True,
            "primary_topic": primary_topic.topic_id,
            "secondary_topic": secondary_topic.topic_id,
            "keywords": keywords,
            "quality_case": quality_case,
            "portfolio_notice": "Generated sample data for UI and analytics preview.",
        }
        topics = [
            {
                "topic_id": primary_topic.topic_id,
                "name": primary_topic.topic_name,
                "name_en": primary_topic.topic_name_en,
                "color": primary_topic.color,
                "keywords": keywords[:3],
                "role": "primary",
            },
            {
                "topic_id": secondary_topic.topic_id,
                "name": secondary_topic.topic_name,
                "name_en": secondary_topic.topic_name_en,
                "color": secondary_topic.color,
                "keywords": [secondary_keyword.keyword],
                "role": "secondary",
            },
        ]
        return NormalizedPost(
            source_id=source_id,
            source_name=spec.name,
            source_type=spec.source_type,
            platform=spec.platform,
            external_id=external_id,
            post_id=index if spec.platform == "dcard" else None,
            forum_alias=board if spec.platform == "dcard" else None,
            board_or_forum=board,
            title=title,
            author_display=f"{spec.platform}-demo-user",
            excerpt=content[:90],
            content=content,
            published_at=published_at.isoformat(),
            created_at=published_at.isoformat(),
            updated_at=(published_at + timedelta(hours=1)).isoformat(),
            like_count=like_count,
            comment_count=comment_count,
            share_count=self.random.randint(0, 80) if spec.platform == "news" else 0,
            view_count=view_count,
            topics=topics,
            url=url,
            canonical_url=url,
            crawl_source="demo",
            raw_json=raw_json,
            content_hash=content_hash(title, content, url),
            language="zh-TW",
        )

    def _topic_content(
        self,
        *,
        primary_topic: TopicDefinition,
        secondary_topic: TopicDefinition,
        keywords: list[str],
        board: str,
        platform: str,
    ) -> str:
        """Build richer sample text with multiple taxonomy keywords."""
        focus = "、".join(keywords[:3])
        related = keywords[-1]
        angles = [
            "討論集中在資料來源治理、趨勢變化與可驗證的分析證據",
            "使用者關注風險、成本、實務經驗與後續影響",
            "跨平台聲量顯示不同社群對同一議題有不同互動模式",
            "留言與文章標題反映短期熱度、長期職涯和產業判斷",
        ]
        return (
            f"{primary_topic.topic_name} 在 {platform} / {board} 的討論持續升溫，"
            f"核心關鍵字包含 {focus}，並與 {secondary_topic.topic_name} 的 {related} 形成共現。"
            f"{self.random.choice(angles)}。這筆資料用來展示公開論壇與新聞資料如何被 "
            "normalize、去重、進行 topic mining、產生視覺化分析並輸出 Excel 報表。"
        )

    def _metric_value(self, platform: str, metric: str) -> int:
        if platform == "ptt":
            values = {"like": 0, "comment": self.random.randint(0, 120), "view": 0}
            return values[metric]
        if platform == "dcard":
            values = {
                "like": self.random.randint(0, 900),
                "comment": self.random.randint(0, 180),
                "view": 0,
            }
            return values[metric]
        values = {
            "like": self.random.randint(0, 180),
            "comment": self.random.randint(0, 90),
            "view": self.random.randint(500, 25000),
        }
        return values[metric]

    def _seed_jobs(self, source_ids: dict[str, int]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        scenarios = [
            ("demo-ptt", "ptt_posts", "completed", None, 18, 120),
            ("demo-news", "news_rss", "completed", None, 9, 80),
            ("demo-dcard", "dcard_posts", "failed", "http_403_forbidden", 1, 0),
            (
                "demo-ptt",
                "ptt_posts",
                "completed_with_warnings",
                "robots_unavailable_opt_in",
                6,
                36,
            ),
            ("demo-news", "news_sitemap", "completed", None, 12, 96),
            ("demo-dcard", "dcard_diagnostics", "completed_with_warnings", "policy_blocked", 2, 0),
            ("demo-news", "news_rss", "failed", "http_429_rate_limited", 3, 0),
        ]
        for source_name, job_type, status, category, requests, items in scenarios:
            spec = next(item for item in DEMO_SOURCES if item.name == source_name)
            job_id = self.crawl_job_repository.start(
                source_ids[source_name],
                job_type,
                target_url=f"{spec.base_url.rstrip('/')}/demo",
            )
            if status == "completed":
                self.crawl_job_repository.finish(job_id, request_count=requests, item_count=items)
            elif status == "completed_with_warnings":
                self.crawl_job_repository.warn(
                    job_id,
                    warning_message=f"Demo warning: {category}",
                    request_count=requests,
                    item_count=items,
                    error_category=category or "data_quality_warning",
                    error_reason=category,
                )
            else:
                self.crawl_job_repository.fail(
                    job_id,
                    error_message=f"Demo fail-closed stop condition: {category}",
                    request_count=requests,
                    item_count=items,
                    error_category=category,
                    error_reason=category,
                )
            jobs.append(
                {
                    "job_id": job_id,
                    "source": source_name,
                    "platform": spec.platform,
                    "job_type": job_type,
                    "status": status,
                    "error_category": category,
                    "request_count": requests,
                    "item_count": items,
                }
            )
        return jobs

    def _write_reports(self, *, rows: int, jobs: list[dict[str, Any]]) -> list[str]:
        crawl_dir = self.report_root / "crawl_runs"
        diagnostics_dir = self.report_root / "diagnostics"
        crawl_dir.mkdir(parents=True, exist_ok=True)
        diagnostics_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now().isoformat()
        crawl_report = crawl_dir / "demo_seed_crawl_report.json"
        crawl_report.write_text(
            json.dumps(
                {
                    "demo": True,
                    "platform": "multi-platform",
                    "source": "demo-seed",
                    "generated_at": now,
                    "stats": {
                        "status": "completed_with_warnings",
                        "rows": rows,
                        "jobs": len(jobs),
                    },
                    "jobs": jobs,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        diagnostics_report = diagnostics_dir / "demo_policy_diagnostics.json"
        diagnostics_report.write_text(
            json.dumps(
                {
                    "demo": True,
                    "platform": "multi-platform",
                    "source": "demo-seed",
                    "generated_at": now,
                    "summary": {
                        "status": "completed_with_warnings",
                        "policy_blocked": 2,
                        "rate_limited": 1,
                        "robots_unavailable_opt_in": 1,
                    },
                    "stop_conditions": [
                        "http_403_forbidden",
                        "http_429_rate_limited",
                        "robots_unavailable_opt_in",
                        "policy_blocked",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return [str(crawl_report), str(diagnostics_report)]
