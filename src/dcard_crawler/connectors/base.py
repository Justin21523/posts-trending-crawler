"""Base connector contract for public data platforms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from dcard_crawler.schemas import NormalizedPost


@dataclass(frozen=True)
class ConnectorTarget:
    """A crawl target such as a forum board, RSS feed, or sitemap."""

    url: str
    label: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ConnectorItem:
    """Raw item returned by a connector before normalization."""

    external_id: str
    raw: Any
    url: str | None = None


class BaseConnector(ABC):
    """Abstract base class all platform connectors must implement."""

    name: str
    source_type: str
    allowed_domains: tuple[str, ...]

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return whether the connector can handle a URL."""

    @abstractmethod
    async def discover_targets(self) -> list[ConnectorTarget]:
        """Discover crawl targets."""

    @abstractmethod
    async def fetch_listing(self, target: ConnectorTarget, **kwargs) -> list[ConnectorItem]:
        """Fetch listing items for a target."""

    @abstractmethod
    async def fetch_detail(self, item: ConnectorItem) -> ConnectorItem | None:
        """Fetch detail data for a listing item."""

    @abstractmethod
    def parse_item(self, raw: Any) -> ConnectorItem:
        """Parse a raw platform object into a connector item."""

    @abstractmethod
    def normalize_item(self, item: ConnectorItem) -> NormalizedPost:
        """Normalize an item into the shared post schema."""
