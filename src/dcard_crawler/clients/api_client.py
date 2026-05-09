"""HTTP client for Dcard API endpoints with rate limiting and retry logic."""

import time

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from dcard_crawler.schemas import PostDetail, PostListItem
from dcard_crawler.settings import settings


class DcardAPIClient:
    """Async HTTP client for Dcard API with built-in rate limiting and retries."""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
    ):
        self.base_url = base_url or settings.dcard_api_base_url
        self.rate_limit = rate_limit or settings.crawler.rate_limit_per_second
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.dcard.tw/",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                verify=settings.ssl_verify,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await httpx.AsyncClient().sleep(wait_time)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry and error handling."""
        await self._rate_limit_wait()
        client = await self._get_client()

        response = await client.request(method, url, **kwargs)

        if response.status_code == 429:
            logger.warning("Rate limited (429). Backing off...")
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
        elif response.status_code >= 400:
            logger.warning(f"HTTP {response.status_code} for {url}")
            response.raise_for_status()

        return response

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
                logger.error(f"Task failed: {result}")
                continue
            pid, detail = result
            post_details[pid] = detail

        return post_details
