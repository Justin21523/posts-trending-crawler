"""Connector registry for platform-specific crawlers."""

from dcard_crawler.connectors.base import BaseConnector
from dcard_crawler.connectors.dcard import DcardConnector
from dcard_crawler.connectors.news import NewsConnector
from dcard_crawler.connectors.ptt import PttConnector


class ConnectorRegistry:
    """Registry for selecting connectors by name or URL."""

    def __init__(self, connectors: list[BaseConnector] | None = None):
        self._connectors: dict[str, BaseConnector] = {}
        for connector in connectors or []:
            self.register(connector)

    def register(self, connector: BaseConnector) -> None:
        """Register a connector instance."""
        self._connectors[connector.name] = connector

    def get(self, name: str) -> BaseConnector:
        """Return a connector by name."""
        try:
            return self._connectors[name]
        except KeyError as exc:
            raise KeyError(f"Connector is not registered: {name}") from exc

    def find_for_url(self, url: str) -> BaseConnector:
        """Return the first connector that can handle a URL."""
        for connector in self._connectors.values():
            if connector.can_handle(url):
                return connector
        raise KeyError(f"No connector can handle URL: {url}")

    def names(self) -> list[str]:
        """Return registered connector names."""
        return sorted(self._connectors)


def default_registry() -> ConnectorRegistry:
    """Create the default connector registry."""
    return ConnectorRegistry([DcardConnector(), PttConnector(), NewsConnector()])
