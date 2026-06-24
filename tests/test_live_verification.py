"""Tests for live verification orchestration without live network."""

import json

import pytest

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.database import init_db
from dcard_crawler.models import CrawlJob
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.services.live_verification import DataQualityGate, LiveVerificationService
from dcard_crawler.settings import settings


class FakeVerificationConnector(BaseConnector):
    name = "fake"
    source_type = "forum"
    allowed_domains = ("example.com",)

    def __init__(self, *, empty_content: bool = False):
        self.empty_content = empty_content
        self.request_count = 0

    def can_handle(self, url: str) -> bool:
        return "example.com" in url

    async def discover_targets(self):
        return [ConnectorTarget("https://example.com/list", "fake")]

    async def fetch_listing(self, target: ConnectorTarget, **kwargs):
        self.request_count += 1
        return [
            ConnectorItem(
                external_id="one",
                raw={"external_id": "one", "content": ""},
                url="https://example.com/one",
            )
        ]

    async def fetch_detail(self, item: ConnectorItem):
        self.request_count += 1
        content = "" if self.empty_content else "Full content long enough for verification"
        return ConnectorItem(
            external_id=item.external_id,
            raw={"external_id": item.external_id, "content": content},
            url=item.url,
        )

    def parse_item(self, raw):
        return ConnectorItem(external_id=raw["external_id"], raw=raw)

    def normalize_item(self, item: ConnectorItem):
        return NormalizedPost(
            source_name="fake",
            source_type="forum",
            platform="fake",
            external_id=item.external_id,
            title="Fake title",
            board_or_forum="fake-board",
            excerpt=item.raw.get("content", ""),
            content=item.raw.get("content", ""),
            published_at="2024-01-01T12:00:00",
            created_at="2024-01-01T12:00:00",
            url=item.url,
            canonical_url=item.url,
            content_hash=f"hash-{item.external_id}",
            raw_json=item.raw,
        )


def build_service(tmp_path, monkeypatch, connector):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    return ConnectorIngestService(connector=connector)


@pytest.mark.asyncio
async def test_live_verification_writes_report_and_quality_passes(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch, FakeVerificationConnector())
    verifier = LiveVerificationService(report_dir=tmp_path / "reports")

    report = await verifier.verify_connector(
        service,
        platform="fake",
        source_name="fake",
        target=ConnectorTarget("https://example.com/list", "fake"),
        max_posts=1,
    )

    report_path = tmp_path / "reports" / report["report_path"].split("/")[-1]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["quality"]["status"] == "passed"
    assert payload["samples"][0]["title"] == "Fake title"
    assert payload["stats"]["items_stored"] == 1


@pytest.mark.asyncio
async def test_live_verification_marks_quality_warning(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch, FakeVerificationConnector(empty_content=True))
    verifier = LiveVerificationService(report_dir=tmp_path / "reports")

    report = await verifier.verify_connector(
        service,
        platform="fake",
        source_name="fake",
        target=ConnectorTarget("https://example.com/list", "fake"),
        max_posts=1,
    )

    job = CrawlJobRepository().get_by_id(report["job_id"])
    assert isinstance(job, CrawlJob)
    assert report["quality"]["status"] == "warning"
    assert report["stats"]["status"] == "completed_with_warnings"
    assert job.status == "completed_with_warnings"
    assert job.error_category == "data_quality_warning"


def test_data_quality_gate_fails_when_no_items_listed():
    result = DataQualityGate().evaluate([], attempted_items=0)

    assert result["status"] == "failed"
    assert "no items were listed" in result["issues"]
