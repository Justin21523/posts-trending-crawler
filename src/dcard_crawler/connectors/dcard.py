"""Dcard connector implementation."""

from urllib.parse import urlparse

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.core.errors import CrawlerError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.schemas import NormalizedPost, PostDetail, PostListItem
from dcard_crawler.settings import settings


class DcardConnector(BaseConnector):
    """Connector for public Dcard forum post endpoints."""

    name = "dcard"
    source_type = "forum"
    allowed_domains = ("www.dcard.tw",)

    def __init__(
        self,
        http_client: CrawlerHttpClient | None = None,
        parser: PostParser | None = None,
    ):
        self.http_client = http_client or CrawlerHttpClient(base_url=settings.dcard_api_base_url)
        self.parser = parser or PostParser()
        self._forum_alias_by_id: dict[str, str] = {}

    @property
    def request_count(self) -> int:
        """Return connector request count when supported by the HTTP client."""
        return int(getattr(self.http_client, "request_count", 0))

    def can_handle(self, url: str) -> bool:
        """Return whether this connector handles the URL."""
        return urlparse(url).netloc.lower() in self.allowed_domains

    async def discover_targets(self) -> list[ConnectorTarget]:
        """Return the configured default Dcard target."""
        forum = settings.dcard_forum_alias
        return [ConnectorTarget(url=f"https://www.dcard.tw/f/{forum}", label=forum)]

    async def fetch_listing(
        self,
        target: ConnectorTarget,
        before: int | None = None,
        limit: int | None = None,
        popular: bool = False,
    ) -> list[ConnectorItem]:
        """Fetch Dcard listing items."""
        forum_alias = target.label
        params = {
            "popular": str(popular).lower(),
            "limit": limit or settings.crawler.batch_size,
        }
        if before:
            params["before"] = str(before)

        data = await self.http_client.get_json(f"/forums/{forum_alias}/posts", params=params)
        items = []
        for raw in data:
            item = self.parse_item(raw)
            self._forum_alias_by_id[item.external_id] = forum_alias
            items.append(item)
        return items

    async def fetch_detail(self, item: ConnectorItem) -> ConnectorItem | None:
        """Fetch Dcard post detail for an item."""
        try:
            data = await self.http_client.get_json(f"/posts/{item.external_id}")
        except CrawlerError as exc:
            if exc.status_code == 404:
                return None
            raise
        return ConnectorItem(
            external_id=item.external_id,
            raw=data,
            url=data.get("url") if isinstance(data, dict) else item.url,
        )

    def parse_item(self, raw) -> ConnectorItem:
        """Parse raw Dcard API object."""
        return ConnectorItem(
            external_id=str(raw["id"]),
            raw=raw,
            url=raw.get("url") if isinstance(raw, dict) else None,
        )

    def normalize_item(self, item: ConnectorItem) -> NormalizedPost:
        """Normalize listing or detail data."""
        raw = item.raw
        if isinstance(raw, PostDetail):
            return self.parser.normalize_detail(raw)
        if isinstance(raw, PostListItem):
            forum_alias = self._forum_alias_by_id.get(str(raw.id), settings.dcard_forum_alias)
            return self.parser.normalize_list_item(raw, forum_alias)

        if isinstance(raw, dict) and ("content" in raw or raw.get("forum_alias")):
            return self.parser.normalize_detail(PostDetail(**raw))

        forum_alias = self._forum_alias_by_id.get(item.external_id, settings.dcard_forum_alias)
        return self.parser.normalize_list_item(PostListItem(**raw), forum_alias)

    async def close(self) -> None:
        """Close connector resources."""
        await self.http_client.close()
