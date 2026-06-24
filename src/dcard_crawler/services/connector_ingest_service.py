"""Generic ingestion service for non-Dcard connectors."""

from datetime import datetime

from loguru import logger

from dcard_crawler.connectors.base import BaseConnector, ConnectorTarget
from dcard_crawler.core.errors import CrawlerError, ErrorCategory, PolicyBlockedError
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.services.quality_service import QualityService


class ConnectorIngestService:
    """Service for crawling connector listing/detail items into normalized posts."""

    def __init__(
        self,
        connector: BaseConnector,
        repository: PostRepository | None = None,
        quality_service: QualityService | None = None,
        source_repository: SourceRepository | None = None,
        crawl_job_repository: CrawlJobRepository | None = None,
    ):
        self.connector = connector
        self.repository = repository or PostRepository()
        self.quality_service = quality_service or QualityService()
        self.source_repository = source_repository or SourceRepository()
        self.crawl_job_repository = crawl_job_repository or CrawlJobRepository()

    async def crawl_target(
        self,
        target: ConnectorTarget,
        *,
        max_pages: int = 1,
        max_posts: int | None = None,
        fetch_details: bool = True,
        source_base_url: str | None = None,
        robots_url: str | None = None,
        **listing_kwargs,
    ) -> dict:
        """Crawl a generic connector target."""
        source_id = self.source_repository.get_or_create(
            name=self.connector.name,
            source_type=self.connector.source_type,
            base_url=source_base_url,
            robots_url=robots_url,
        )
        job_id = self.crawl_job_repository.start(
            source_id=source_id,
            job_type=f"{self.connector.name}_posts",
            target_url=target.url,
        )
        stats = {
            "job_id": job_id,
            "source": self.connector.name,
            "target": target.label,
            "items_listed": 0,
            "items_stored": 0,
            "items_detailed": 0,
            "items_skipped": 0,
            "errors": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error_category": None,
            "error_reason": None,
        }
        fatal_error: Exception | None = None

        try:
            for page in range(1, max_pages + 1):
                if max_posts is not None and stats["items_listed"] >= max_posts:
                    break
                items = await self.connector.fetch_listing(target, page=page, **listing_kwargs)
                if not items:
                    break

                for item in items:
                    if max_posts is not None and stats["items_listed"] >= max_posts:
                        break
                    stats["items_listed"] += 1
                    try:
                        normalized = self.connector.normalize_item(item)
                        normalized.source_id = source_id
                        if self.repository.exists_external(source_id, normalized.external_id):
                            stats["items_skipped"] += 1
                            continue
                        is_valid, issues = self.quality_service.validate(normalized)
                        if not is_valid:
                            logger.warning(f"Item {item.external_id} validation issues: {issues}")
                        self.repository.upsert(normalized)
                        stats["items_stored"] += 1

                        if fetch_details:
                            detail_item = await self.connector.fetch_detail(item)
                            if detail_item is None:
                                continue
                            detail = self.connector.normalize_item(detail_item)
                            detail.source_id = source_id
                            is_valid, issues = self.quality_service.validate(detail)
                            if not is_valid:
                                logger.warning(
                                    f"Detail {item.external_id} validation issues: {issues}"
                                )
                            self.repository.upsert(detail)
                            stats["items_detailed"] += 1
                    except PolicyBlockedError:
                        raise
                    except Exception as exc:
                        logger.error(f"Failed to process connector item {item.external_id}: {exc}")
                        stats["errors"] += 1
        except PolicyBlockedError as exc:
            fatal_error = exc
            stats["errors"] += 1
            stats["error_category"] = exc.category.value
            stats["error_reason"] = str(exc)
        except Exception as exc:
            fatal_error = exc
            stats["errors"] += 1
        finally:
            stats["completed_at"] = datetime.now().isoformat()
            request_count = int(getattr(self.connector, "request_count", 0))
            if fatal_error or stats["errors"]:
                error_category = stats["error_category"] or self._error_category(fatal_error)
                error_reason = stats["error_reason"] or str(fatal_error or "completed_with_errors")
                stats["status"] = "failed"
                stats["error_category"] = error_category
                stats["error_reason"] = error_reason
                self.crawl_job_repository.fail(
                    job_id,
                    error_message=error_reason,
                    request_count=request_count,
                    item_count=stats["items_stored"],
                    error_category=error_category,
                    error_reason=error_reason,
                )
            else:
                stats["status"] = "completed"
                self.crawl_job_repository.finish(
                    job_id,
                    request_count=request_count,
                    item_count=stats["items_stored"],
                )
        return stats

    async def close(self) -> None:
        """Close connector resources."""
        close_connector = getattr(self.connector, "close", None)
        if close_connector:
            await close_connector()

    @staticmethod
    def _error_category(error: Exception | None) -> str:
        if isinstance(error, CrawlerError):
            return error.category.value
        return ErrorCategory.UNKNOWN.value
