"""Tests for source catalog and batch crawl service."""

from pathlib import Path

import pytest

from dcard_crawler.services.batch_crawl import BatchCrawlService
from dcard_crawler.services.source_catalog import load_source_catalog

CATALOG_TEXT = """
groups:
  news:
    - name: local-news
      display_name: Local News
      platform: news
      source_type: news
      strategy: rss
      enabled: true
      base_url: https://news.example.com
      target_url: https://news.example.com/rss.xml
      robots_url: https://news.example.com/robots.txt
      default_max_items: 10
      default_max_pages: 1
      tags: [news]
  ptt:
    - name: local-ptt
      display_name: Local PTT
      platform: ptt
      source_type: forum
      strategy: ptt_board
      enabled: true
      base_url: https://www.ptt.cc
      board: Stock
      robots_url: https://www.ptt.cc/robots.txt
      default_max_items: 10
      default_max_pages: 1
      allow_robots_unavailable: true
      tags: [ptt]
    - name: disabled-ptt
      display_name: Disabled PTT
      platform: ptt
      source_type: forum
      strategy: ptt_board
      enabled: false
      base_url: https://www.ptt.cc
      board: NBA
      robots_url: https://www.ptt.cc/robots.txt
      default_max_items: 10
      default_max_pages: 1
"""


class FakeConnector:
    @staticmethod
    def board_target(board):
        from dcard_crawler.connectors.base import ConnectorTarget

        return ConnectorTarget(url=f"https://www.ptt.cc/bbs/{board}/index.html", label=board)


class FakeService:
    connector = FakeConnector()
    closed = False

    async def crawl_target(self, target, **kwargs):
        return {
            "job_id": 1,
            "status": "completed",
            "items_listed": kwargs["max_posts"],
            "items_stored": kwargs["max_posts"],
            "items_skipped": 0,
            "request_count": 2,
        }

    async def close(self):
        self.closed = True


class FailingService(FakeService):
    async def crawl_target(self, target, **kwargs):
        raise RuntimeError("blocked by fake policy")


def write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(CATALOG_TEXT, encoding="utf-8")
    return path


def test_load_source_catalog_selects_enabled_entries(tmp_path):
    catalog = load_source_catalog(write_catalog(tmp_path))

    assert [entry.name for entry in catalog.enabled_entries("ptt")] == ["local-ptt"]
    assert catalog.select(names=["local-news"])[0].target_url == "https://news.example.com/rss.xml"


@pytest.mark.asyncio
async def test_batch_crawl_dry_run_lists_selected_sources(tmp_path):
    service = BatchCrawlService(catalog_path=write_catalog(tmp_path))

    report = await service.crawl(group="ptt", dry_run=True)

    assert report["dry_run"] is True
    assert report["summary"]["total"] == 1
    assert report["results"][0]["source"] == "local-ptt"
    assert report["results"][0]["status"] == "dry_run"


@pytest.mark.asyncio
async def test_batch_crawl_records_partial_failure(tmp_path):
    path = write_catalog(tmp_path)
    service = BatchCrawlService(
        catalog_path=path,
        report_root=tmp_path / "reports",
        news_builder=lambda **kwargs: FakeService(),
        ptt_builder=lambda **kwargs: FailingService(),
    )

    report = await service.crawl(group=None, max_items_per_source=3, max_pages=1)

    assert report["summary"]["total"] == 2
    assert report["summary"]["completed"] == 1
    assert report["summary"]["failed"] == 1
    assert (tmp_path / "reports").exists()
