"""Ingestion service for orchestrating the crawl pipeline."""

import asyncio
from datetime import datetime

from loguru import logger

from dcard_crawler.clients.api_client import DcardAPIClient
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.schemas import Checkpoint
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
    ):
        self.api_client = api_client
        self.repository = repository
        self.parser = parser
        self.quality_service = quality_service
        self.checkpoint_service = checkpoint_service

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
        }

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
                    posts = await self.api_client.fetch_forum_posts(
                        forum_alias=forum_alias,
                        before=before_id,
                        limit=batch_size,
                        popular=popular,
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch post listing: {e}")
                    stats["errors"] += 1
                    break

                if not posts:
                    logger.info("No more posts to fetch (end of feed)")
                    break

                logger.info(f"Received {len(posts)} posts in batch")
                stats["posts_listed"] += len(posts)

                # Process each post
                post_ids_for_detail = []
                for post_item in posts:
                    try:
                        # Skip if already exists
                        if self.repository.exists(post_item.id):
                            logger.debug(f"Post {post_item.id} already exists, skipping")
                            stats["posts_skipped"] += 1
                            total_fetched += 1
                            continue

                        # Normalize and validate
                        normalized = self.parser.normalize_list_item(post_item, forum_alias)
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

                        post_ids_for_detail.append(post_item.id)
                        total_fetched += 1

                        # Update before_id for next page
                        before_id = post_item.id

                    except Exception as e:
                        logger.error(f"Error processing post {post_item.id}: {e}")
                        stats["errors"] += 1

                # Fetch details if requested
                if fetch_details and post_ids_for_detail:
                    logger.info(f"Fetching details for {len(post_ids_for_detail)} posts")
                    try:
                        details = await self.api_client.fetch_multiple_post_details(
                            post_ids_for_detail,
                            concurrency=5,
                        )

                        for pid, detail in details.items():
                            if detail:
                                try:
                                    normalized_detail = (
                                        self.parser.normalize_detail(detail)
                                    )
                                    is_valid, issues = (
                                        self.quality_service.validate(
                                            normalized_detail
                                        )
                                    )

                                    if is_valid:
                                        self.repository.upsert(normalized_detail)
                                        stats["posts_detailed"] += 1
                                    else:
                                        logger.warning(
                                            f"Post {pid} detail validation "
                                            f"failed: {issues}"
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Failed to store detail for {pid}: {e}"
                                    )
                                    stats["errors"] += 1
                    except Exception as e:
                        logger.error(f"Failed to fetch post details: {e}")
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
        except Exception as e:
            logger.error(f"Crawl failed with exception: {e}")
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

        logger.info(f"Crawl completed: {stats}")
        return stats
