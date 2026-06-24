"""Tests for generic connector ingestion service."""

import pytest

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.core.errors import RateLimitedError, RobotsDisallowedError
from dcard_crawler.database import init_db
from dcard_crawler.models import CrawlJob
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.settings import settings


class FakePttConnector(BaseConnector):
    name = "ptt"
    source_type = "forum"
    allowed_domains = ("www.ptt.cc",)

    def __init__(self, failure: Exception | None = None):
        self.failure = failure
        self.request_count = 0

    def can_handle(self, url: str) -> bool:
        return "ptt.cc" in url

    async def discover_targets(self):
        return [ConnectorTarget("https://www.ptt.cc/bbs/Stock/index.html", "Stock")]

    async def fetch_listing(self, target: ConnectorTarget, **kwargs):
        self.request_count += 1
        if self.failure:
            raise self.failure
        return [
            ConnectorItem(
                external_id="M.1700000000.A.123",
                raw={"external_id": "M.1700000000.A.123"},
                url="https://www.ptt.cc/bbs/Stock/M.1700000000.A.123.html",
            )
        ]

    async def fetch_detail(self, item: ConnectorItem):
        self.request_count += 1
        return ConnectorItem(
            external_id=item.external_id,
            raw={"external_id": item.external_id, "content": "PTT content long enough"},
            url=item.url,
        )

    def parse_item(self, raw):
        return ConnectorItem(external_id=raw["external_id"], raw=raw)

    def normalize_item(self, item: ConnectorItem):
        return NormalizedPost(
            source_name="ptt",
            source_type="forum",
            platform="ptt",
            external_id=item.external_id,
            title="PTT title",
            board_or_forum="Stock",
            content=item.raw.get("content", "PTT excerpt long enough"),
            published_at="2024-01-01T12:00:00",
            created_at="2024-01-01T12:00:00",
            comment_count=5,
            url=item.url,
            canonical_url=item.url,
            raw_json=item.raw,
        )


def build_service(tmp_path, monkeypatch, connector):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    return ConnectorIngestService(connector=connector)


@pytest.mark.asyncio
async def test_generic_ingest_writes_ptt_post_and_deduplicates(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch, FakePttConnector())
    target = ConnectorTarget("https://www.ptt.cc/bbs/Stock/index.html", "Stock")

    stats = await service.crawl_target(target, max_pages=1, max_posts=1)
    stats2 = await service.crawl_target(target, max_pages=1, max_posts=1)

    assert stats["status"] == "completed"
    assert stats["items_stored"] == 1
    assert stats2["items_skipped"] == 1
    assert PostRepository().count() == 1


@pytest.mark.asyncio
async def test_generic_ingest_records_rate_limit_failure(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch, FakePttConnector(RateLimitedError("blocked")))
    target = ConnectorTarget("https://www.ptt.cc/bbs/Stock/index.html", "Stock")

    stats = await service.crawl_target(target, max_pages=1)

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert job.status == "failed"
    assert job.error_category == "rate_limited"


@pytest.mark.asyncio
async def test_generic_ingest_records_robots_failure(tmp_path, monkeypatch):
    service = build_service(
        tmp_path,
        monkeypatch,
        FakePttConnector(RobotsDisallowedError("robots.txt disallows URL")),
    )
    target = ConnectorTarget("https://www.ptt.cc/bbs/Stock/index.html", "Stock")

    stats = await service.crawl_target(target, max_pages=1)

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert job.status == "failed"
    assert job.error_category == "robots_disallowed"
