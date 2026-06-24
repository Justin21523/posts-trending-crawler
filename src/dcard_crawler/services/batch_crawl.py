"""Batch crawling from the configured source catalog."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dcard_crawler.connectors.base import ConnectorTarget
from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.services.factory import build_news_ingest_service, build_ptt_ingest_service
from dcard_crawler.services.source_catalog import SourceCatalogEntry, load_source_catalog

NewsBuilder = Callable[..., ConnectorIngestService]
PttBuilder = Callable[..., ConnectorIngestService]


class BatchCrawlService:
    """Run catalog-driven low-volume source crawls."""

    def __init__(
        self,
        *,
        catalog_path: str | Path | None = None,
        report_root: str | Path = "data/reports/batch_runs",
        news_builder: NewsBuilder = build_news_ingest_service,
        ptt_builder: PttBuilder = build_ptt_ingest_service,
    ) -> None:
        self.catalog_path = catalog_path
        self.report_root = Path(report_root)
        self.news_builder = news_builder
        self.ptt_builder = ptt_builder

    async def crawl(
        self,
        *,
        group: str | None = None,
        source_names: list[str] | None = None,
        max_items_per_source: int | None = None,
        max_pages: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run a batch crawl and return a report-friendly summary."""
        catalog = load_source_catalog(self.catalog_path)
        entries = catalog.select(group=group, names=source_names)
        started_at = datetime.now()
        results: list[dict[str, Any]] = []

        for entry in entries:
            if dry_run:
                results.append(self._dry_run_result(entry, max_items_per_source, max_pages))
                continue
            results.append(
                await self._crawl_entry(
                    entry,
                    max_items=max_items_per_source or entry.default_max_items,
                    max_pages=max_pages or entry.default_max_pages,
                )
            )

        report = {
            "generated_at": datetime.now().isoformat(),
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "group": group,
            "sources_requested": source_names or [],
            "summary": self._summary(results),
            "results": results,
        }
        if not dry_run:
            report["report_path"] = self._write_report(report)
        return report

    async def _crawl_entry(
        self,
        entry: SourceCatalogEntry,
        *,
        max_items: int,
        max_pages: int,
    ) -> dict[str, Any]:
        service = self._build_service(entry)
        try:
            target = self._target(entry)
            stats = await service.crawl_target(
                target,
                max_pages=1 if entry.strategy in {"rss", "sitemap", "article"} else max_pages,
                max_posts=max_items,
                fetch_details=True,
                source_base_url=entry.base_url,
                robots_url=entry.robots_url,
                max_articles=max_items if entry.strategy in {"rss", "sitemap", "article"} else None,
            )
            return {
                "source": entry.name,
                "display_name": entry.display_name,
                "group": entry.group,
                "platform": entry.platform,
                "strategy": entry.strategy,
                "status": stats.get("status", "unknown"),
                "job_id": stats.get("job_id"),
                "items_listed": stats.get("items_listed", 0),
                "items_stored": stats.get("items_stored", 0),
                "items_skipped": stats.get("items_skipped", 0),
                "request_count": stats.get("request_count", 0),
                "error_category": stats.get("error_category"),
                "error_reason": stats.get("error_reason"),
            }
        except Exception as exc:
            return {
                "source": entry.name,
                "display_name": entry.display_name,
                "group": entry.group,
                "platform": entry.platform,
                "strategy": entry.strategy,
                "status": "failed",
                "job_id": None,
                "items_listed": 0,
                "items_stored": 0,
                "items_skipped": 0,
                "request_count": 0,
                "error_category": type(exc).__name__,
                "error_reason": str(exc),
            }
        finally:
            await service.close()

    def _build_service(self, entry: SourceCatalogEntry) -> ConnectorIngestService:
        if entry.strategy in {"rss", "sitemap", "article"}:
            return self.news_builder(source_name=entry.name)
        if entry.strategy == "ptt_board":
            service = self.ptt_builder(
                board=entry.board or "Stock",
                allow_over18_public_confirm=entry.allow_over18_public_confirm,
                robots_unavailable_policy="allow" if entry.allow_robots_unavailable else None,
            )
            service.connector.source_name = entry.name
            return service
        raise ValueError(f"Unsupported catalog strategy: {entry.strategy}")

    @staticmethod
    def _target(entry: SourceCatalogEntry) -> ConnectorTarget:
        if entry.strategy == "ptt_board":
            from dcard_crawler.connectors.ptt import PttConnector

            return PttConnector.board_target(entry.board or "Stock")
        return ConnectorTarget(
            url=entry.target_url or "",
            label=entry.name,
            metadata={"target_type": entry.strategy},
        )

    @staticmethod
    def _dry_run_result(
        entry: SourceCatalogEntry,
        max_items: int | None,
        max_pages: int | None,
    ) -> dict[str, Any]:
        return {
            "source": entry.name,
            "display_name": entry.display_name,
            "group": entry.group,
            "platform": entry.platform,
            "strategy": entry.strategy,
            "status": "dry_run",
            "target": entry.board or entry.target_url,
            "max_items": max_items or entry.default_max_items,
            "max_pages": max_pages or entry.default_max_pages,
        }

    @staticmethod
    def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(results),
            "completed": sum(1 for result in results if result.get("status") == "completed"),
            "failed": sum(1 for result in results if result.get("status") == "failed"),
            "dry_run": sum(1 for result in results if result.get("status") == "dry_run"),
            "items_stored": sum(int(result.get("items_stored") or 0) for result in results),
            "request_count": sum(int(result.get("request_count") or 0) for result in results),
        }

    def _write_report(self, report: dict[str, Any]) -> str:
        self.report_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.report_root / f"batch_crawl_{stamp}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
