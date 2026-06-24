"""Ingestion service for orchestrating the crawl pipeline."""

import asyncio
from datetime import datetime

from loguru import logger

from dcard_crawler.clients.api_client import DcardAPIClient
from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.connectors.dcard import DcardConnector
from dcard_crawler.connectors.registry import ConnectorRegistry, default_registry
from dcard_crawler.core.errors import CrawlerError, ErrorCategory, PolicyBlockedError
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import Checkpoint, PostListItem
from dcard_crawler.services.checkpoint_service import CheckpointService
from dcard_crawler.services.quality_service import QualityService
from dcard_crawler.settings import settings


class IngestService:
    """Service for orchestrating post listing, detail fetching, and storage."""

    def __init__(
        self,
        api_client: DcardAPIClient,
        repository: PostRepository,
        parser: PostParser,
        quality_service: QualityService,
        checkpoint_service: CheckpointService,
        source_repository: SourceRepository | None = None,
        crawl_job_repository: CrawlJobRepository | None = None,
        dcard_connector: DcardConnector | None = None,
        connector_registry: ConnectorRegistry | None = None,
    ):
        self.api_client = api_client
        self.repository = repository
        self.parser = parser
        self.quality_service = quality_service
        self.checkpoint_service = checkpoint_service
        self.source_repository = source_repository or SourceRepository()
        self.crawl_job_repository = crawl_job_repository or CrawlJobRepository()
        self.connector_registry = connector_registry or default_registry()
        if dcard_connector is not None:
            self.connector_registry.register(dcard_connector)
        self.dcard_connector = self.connector_registry.get("dcard")

    async def close(self) -> None:
        """Close service-owned network resources."""
        await self.api_client.close()
        close_connector = getattr(self.dcard_connector, "close", None)
        if close_connector:
            await close_connector()

    async def crawl_posts(
        self,
        forum_alias: str,
        max_posts: int | None = None,
        popular: bool = False,
        fetch_details: bool = True,
        resume: bool = True,
    ) -> dict:
        """Main crawl loop: fetch posts, optionally fetch details, and store them.

        Args:
            forum_alias: Forum alias to crawl
            max_posts: Maximum number of posts to fetch (None for unlimited)
            popular: Whether to fetch popular posts
            fetch_details: Whether to fetch full post details
            resume: Whether to resume from checkpoint

        Returns:
            Summary dict with crawl statistics
        """
        logger.info(f"Starting crawl: forum={forum_alias} popular={popular} max_posts={max_posts}")
        source_id = self.source_repository.get_or_create(
            name="dcard",
            source_type="forum",
            base_url="https://www.dcard.tw",
            robots_url="https://www.dcard.tw/robots.txt",
        )
        target_url = f"https://www.dcard.tw/f/{forum_alias}"
        job_id = self.crawl_job_repository.start(
            source_id=source_id,
            job_type="dcard_posts",
            target_url=target_url,
        )

        # Load checkpoint if resuming
        checkpoint = None
        if resume:
            checkpoint = self.checkpoint_service.load(forum_alias, popular_mode=popular)
            before_id = checkpoint.last_post_id if checkpoint else None
            total_fetched = checkpoint.total_fetched if checkpoint else 0
        else:
            before_id = None
            total_fetched = 0

        stats = {
            "forum_alias": forum_alias,
            "popular": popular,
            "posts_listed": 0,
            "posts_detailed": 0,
            "posts_stored": 0,
            "posts_skipped": 0,
            "errors": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "job_id": job_id,
            "status": "running",
            "error_category": None,
            "error_reason": None,
        }

        fatal_error: Exception | None = None
        try:
            while True:
                # Check if we've reached the limit
                if max_posts and total_fetched >= max_posts:
                    logger.info(f"Reached max_posts limit: {max_posts}")
                    break

                # Calculate batch size
                batch_size = settings.crawler.batch_size
                if max_posts:
                    remaining = max_posts - total_fetched
                    batch_size = min(batch_size, remaining)

                # Fetch batch of posts
                logger.info(f"Fetching batch: before_id={before_id} batch_size={batch_size}")
                try:
                    target = ConnectorTarget(
                        url=f"https://www.dcard.tw/f/{forum_alias}",
                        label=forum_alias,
                    )
                    listing_items = await self.dcard_connector.fetch_listing(
                        target=target,
                        before=before_id,
                        limit=batch_size,
                        popular=popular,
                    )
                    posts = [PostListItem(**item.raw) for item in listing_items]
                except PolicyBlockedError:
                    raise
                except Exception as e:
                    logger.error(f"Failed to fetch post listing: {e}")
                    stats["errors"] += 1
                    fatal_error = e
                    break

                if not posts:
                    logger.info("No more posts to fetch (end of feed)")
                    break

                logger.info(f"Received {len(posts)} posts in batch")
                stats["posts_listed"] += len(posts)

                # Process each post
                items_for_detail: list[ConnectorItem] = []
                for item, post_item in zip(listing_items, posts, strict=False):
                    try:
                        # Skip if already exists
                        if self.repository.exists(post_item.id, source_id=source_id):
                            logger.debug(f"Post {post_item.id} already exists, skipping")
                            stats["posts_skipped"] += 1
                            total_fetched += 1
                            continue

                        # Normalize and validate
                        normalized = self.dcard_connector.normalize_item(item)
                        normalized.source_id = source_id
                        is_valid, issues = self.quality_service.validate(normalized)

                        if not is_valid:
                            logger.warning(f"Post {post_item.id} failed validation: {issues}")

                        # Store the post
                        try:
                            self.repository.upsert(normalized)
                            stats["posts_stored"] += 1
                        except Exception as e:
                            logger.error(f"Failed to store post {post_item.id}: {e}")
                            stats["errors"] += 1

                        items_for_detail.append(item)
                        total_fetched += 1

                        # Update before_id for next page
                        before_id = post_item.id

                    except Exception as e:
                        logger.error(f"Error processing post {post_item.id}: {e}")
                        stats["errors"] += 1

                # Fetch details if requested
                if fetch_details and items_for_detail:
                    logger.info(f"Fetching details for {len(items_for_detail)} posts")
                    for item in items_for_detail:
                        try:
                            detail_item = await self.dcard_connector.fetch_detail(item)
                            if detail_item is None:
                                continue

                            normalized_detail = self.dcard_connector.normalize_item(detail_item)
                            normalized_detail.source_id = source_id
                            is_valid, issues = self.quality_service.validate(normalized_detail)

                            if is_valid:
                                self.repository.upsert(normalized_detail)
                                stats["posts_detailed"] += 1
                            else:
                                logger.warning(
                                    f"Post {item.external_id} detail validation failed: {issues}"
                                )
                        except PolicyBlockedError:
                            raise
                        except Exception as e:
                            logger.error(
                                f"Failed to fetch/store detail for {item.external_id}: {e}"
                            )
                            stats["errors"] += 1

                # Save checkpoint
                checkpoint = Checkpoint(
                    forum_alias=forum_alias,
                    last_post_id=before_id,
                    last_success_at=datetime.now().isoformat(),
                    total_fetched=total_fetched,
                    popular_mode=popular,
                )
                self.checkpoint_service.save(checkpoint)

                # Rest between batches
                if settings.crawler.batch_rest_interval > 0:
                    logger.debug(f"Resting for {settings.crawler.batch_rest_interval}s")
                    await asyncio.sleep(settings.crawler.batch_rest_interval)

        except KeyboardInterrupt:
            logger.warning("Crawl interrupted by user")
            fatal_error = KeyboardInterrupt("Crawl interrupted by user")
            stats["errors"] += 1
        except PolicyBlockedError as e:
            logger.error(f"Crawl stopped by policy: {e}")
            fatal_error = e
            stats["errors"] += 1
            stats["error_category"] = e.category.value
            stats["error_reason"] = str(e)
        except Exception as e:
            logger.error(f"Crawl failed with exception: {e}")
            fatal_error = e
            stats["errors"] += 1
        finally:
            stats["completed_at"] = datetime.now().isoformat()
            # Save final checkpoint
            if before_id:
                final_checkpoint = Checkpoint(
                    forum_alias=forum_alias,
                    last_post_id=before_id,
                    last_success_at=datetime.now().isoformat(),
                    total_fetched=total_fetched,
                    popular_mode=popular,
                )
                self.checkpoint_service.save(final_checkpoint)

            request_count = self._connector_request_count(self.dcard_connector)
            stats["request_count"] = request_count
            if fatal_error or stats["errors"]:
                error_category = stats["error_category"] or self._error_category(fatal_error)
                error_reason = stats["error_reason"] or str(fatal_error or "completed_with_errors")
                stats["status"] = "failed"
                stats["error_category"] = error_category
                stats["error_reason"] = error_reason
                self.crawl_job_repository.fail(
                    job_id=job_id,
                    error_message=error_reason,
                    request_count=request_count,
                    item_count=stats["posts_stored"],
                    error_category=error_category,
                    error_reason=error_reason,
                )
            else:
                stats["status"] = "completed"
                self.crawl_job_repository.finish(
                    job_id=job_id,
                    request_count=request_count,
                    item_count=stats["posts_stored"],
                )

        logger.info(f"Crawl completed: {stats}")
        return stats

    @staticmethod
    def _connector_request_count(connector: BaseConnector) -> int:
        return int(getattr(connector, "request_count", 0))

    @staticmethod
    def _error_category(error: Exception | None) -> str:
        if isinstance(error, CrawlerError):
            return error.category.value
        if isinstance(error, KeyboardInterrupt):
            return "interrupted"
        return ErrorCategory.UNKNOWN.value
