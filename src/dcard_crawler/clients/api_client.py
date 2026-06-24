"""Compatibility client for Dcard API endpoints."""

import httpx
from loguru import logger

from dcard_crawler.core.errors import CrawlerError, PolicyBlockedError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.schemas import PostDetail, PostListItem
from dcard_crawler.settings import settings


class DcardAPIClient:
    """Async Dcard API client backed by the shared crawler core."""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
    ):
        self.base_url = base_url or settings.dcard_api_base_url
        self.rate_limit = rate_limit or settings.crawler.rate_limit_per_second
        self.headers = {
            **CrawlerHttpClient.default_headers(),
            "Accept": "application/json",
            "Referer": "https://www.dcard.tw/",
        }
        self._client = CrawlerHttpClient(base_url=self.base_url, headers=self.headers)

    @property
    def request_count(self) -> int:
        """Return total requests made by the compatibility client."""
        return self._client.request_count

    async def close(self) -> None:
        await self._client.close()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with shared policy checks."""
        return await self._client.request(method, url, **kwargs)

    async def fetch_forum_posts(
        self,
        forum_alias: str,
        before: int | None = None,
        limit: int | None = None,
        popular: bool = False,
    ) -> list[PostListItem]:
        """Fetch posts from forum listing endpoint.

        Args:
            forum_alias: Forum alias (e.g., 'trending')
            before: Post ID to fetch posts before (for pagination)
            limit: Number of posts to fetch
            popular: Whether to fetch popular posts

        Returns:
            List of PostListItem objects
        """
        url = f"/forums/{forum_alias}/posts"
        params = {
            "popular": str(popular).lower(),
            "limit": limit or settings.crawler.batch_size,
        }
        if before:
            params["before"] = str(before)

        logger.info(f"Fetching forum posts: {url} params={params}")

        response = await self._request("GET", url, params=params)
        data = response.json()

        posts = []
        for item in data:
            try:
                post = PostListItem(**item)
                posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse post item: {e}")
                continue

        logger.info(f"Fetched {len(posts)} posts from {forum_alias}")
        return posts

    async def fetch_post_detail(self, post_id: int) -> PostDetail | None:
        """Fetch full post data from detail endpoint.

        Args:
            post_id: The post ID to fetch

        Returns:
            PostDetail object or None if not found
        """
        url = f"/posts/{post_id}"
        logger.info(f"Fetching post detail: {url}")

        try:
            response = await self._request("GET", url)
            data = response.json()
            post = PostDetail(**data)
            return post
        except PolicyBlockedError:
            raise
        except CrawlerError as e:
            if e.status_code == 404:
                logger.warning(f"Post {post_id} not found")
                return None
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Post {post_id} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to fetch post {post_id}: {e}")
            return None

    async def fetch_multiple_post_details(
        self, post_ids: list[int], concurrency: int = 5
    ) -> dict[int, PostDetail | None]:
        """Fetch multiple post details with controlled concurrency.

        Args:
            post_ids: List of post IDs to fetch
            concurrency: Maximum concurrent requests

        Returns:
            Dict mapping post_id to PostDetail or None
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def _fetch_with_limit(pid: int) -> tuple[int, PostDetail | None]:
            async with semaphore:
                detail = await self.fetch_post_detail(pid)
                return pid, detail

        tasks = [_fetch_with_limit(pid) for pid in post_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        post_details = {}
        for result in results:
            if isinstance(result, Exception):
                if isinstance(result, PolicyBlockedError):
                    raise result
                logger.error(f"Task failed: {result}")
                continue
            pid, detail = result
            post_details[pid] = detail

        return post_details
