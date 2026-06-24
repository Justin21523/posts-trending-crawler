"""Tests for crawl job lifecycle behavior in IngestService."""

import pytest

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.core.errors import (
    RateLimitedError,
    RequestBudgetExceededError,
    RobotsDisallowedError,
)
from dcard_crawler.database import init_db
from dcard_crawler.models import CrawlJob
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost, PostDetail, PostListItem
from dcard_crawler.services.checkpoint_service import CheckpointService
from dcard_crawler.services.ingest_service import IngestService
from dcard_crawler.services.quality_service import QualityService
from dcard_crawler.settings import settings


class FakeDcardConnector(BaseConnector):
    name = "dcard"
    source_type = "forum"
    allowed_domains = ("www.dcard.tw",)

    def __init__(self, *, failure: Exception | None = None):
        self.failure = failure
        self.request_count = 0
        self.parser = PostParser()

    def can_handle(self, url: str) -> bool:
        return "www.dcard.tw" in url

    async def discover_targets(self) -> list[ConnectorTarget]:
        return [ConnectorTarget(url="https://www.dcard.tw/f/trending", label="trending")]

    async def fetch_listing(self, target: ConnectorTarget, **kwargs) -> list[ConnectorItem]:
        self.request_count += 1
        if self.failure:
            raise self.failure
        return [
            ConnectorItem(
                external_id="12345",
                raw={
                    "id": 12345,
                    "title": "Test title",
                    "excerpt": "Long enough excerpt",
                    "created_at": "2024-01-01T12:00:00Z",
                    "comment_count": 1,
                    "like_count": 2,
                    "topics": [],
                },
            )
        ]

    async def fetch_detail(self, item: ConnectorItem) -> ConnectorItem | None:
        self.request_count += 1
        return ConnectorItem(
            external_id=item.external_id,
            raw={
                "id": int(item.external_id),
                "title": "Test title",
                "excerpt": "Long enough excerpt",
                "content": "Long enough detail content",
                "created_at": "2024-01-01T12:00:00Z",
                "comment_count": 1,
                "like_count": 2,
                "topics": [],
                "forum_alias": "trending",
                "forum_name": "Trending",
                "media": [],
            },
        )

    def parse_item(self, raw) -> ConnectorItem:
        return ConnectorItem(external_id=str(raw["id"]), raw=raw)

    def normalize_item(self, item: ConnectorItem) -> NormalizedPost:
        if "content" in item.raw:
            return self.parser.normalize_detail(PostDetail(**item.raw))
        return self.parser.normalize_list_item(PostListItem(**item.raw), "trending")


class FakeApiClient:
    async def close(self):
        return None


def build_service(tmp_path, monkeypatch, connector: FakeDcardConnector) -> IngestService:
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    checkpoint_path = tmp_path / "checkpoint.json"

    return IngestService(
        api_client=FakeApiClient(),
        repository=PostRepository(),
        parser=PostParser(),
        quality_service=QualityService(),
        checkpoint_service=CheckpointService(str(checkpoint_path)),
        source_repository=SourceRepository(),
        crawl_job_repository=CrawlJobRepository(),
        dcard_connector=connector,
    )


@pytest.mark.asyncio
async def test_ingest_service_marks_job_completed(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch, FakeDcardConnector())

    stats = await service.crawl_posts(
        forum_alias="trending",
        max_posts=1,
        fetch_details=True,
        resume=False,
    )

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert stats["status"] == "completed"
    assert job.status == "completed"
    assert job.request_count == 2
    assert job.item_count == 1


@pytest.mark.asyncio
async def test_ingest_service_marks_policy_error_failed(tmp_path, monkeypatch):
    service = build_service(
        tmp_path,
        monkeypatch,
        FakeDcardConnector(
            failure=RateLimitedError("Request blocked by policy: http_429_rate_limited")
        ),
    )

    stats = await service.crawl_posts(
        forum_alias="trending",
        max_posts=1,
        fetch_details=True,
        resume=False,
    )

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert stats["status"] == "failed"
    assert stats["error_category"] == "rate_limited"
    assert job.status == "failed"
    assert job.error_category == "rate_limited"
    assert job.request_count == 1


@pytest.mark.asyncio
async def test_ingest_service_records_request_budget_error(tmp_path, monkeypatch):
    service = build_service(
        tmp_path,
        monkeypatch,
        FakeDcardConnector(failure=RequestBudgetExceededError("Request budget exceeded")),
    )

    stats = await service.crawl_posts(
        forum_alias="trending",
        max_posts=1,
        fetch_details=False,
        resume=False,
    )

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert stats["status"] == "failed"
    assert job.error_category == "budget_exceeded"


@pytest.mark.asyncio
async def test_ingest_service_records_robots_disallowed_error(tmp_path, monkeypatch):
    service = build_service(
        tmp_path,
        monkeypatch,
        FakeDcardConnector(failure=RobotsDisallowedError("robots.txt disallows URL")),
    )

    stats = await service.crawl_posts(
        forum_alias="trending",
        max_posts=1,
        fetch_details=False,
        resume=False,
    )

    job = CrawlJobRepository().get_by_id(stats["job_id"])
    assert isinstance(job, CrawlJob)
    assert stats["status"] == "failed"
    assert job.error_category == "robots_disallowed"
