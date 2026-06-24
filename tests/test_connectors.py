"""Tests for connector contracts and Dcard connector behavior."""

import pytest

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.connectors.dcard import DcardConnector
from dcard_crawler.connectors.registry import ConnectorRegistry
from dcard_crawler.core.errors import RateLimitedError


class IncompleteConnector(BaseConnector):
    name = "incomplete"
    source_type = "forum"
    allowed_domains = ("example.com",)


def test_base_connector_contract_requires_methods():
    with pytest.raises(TypeError):
        IncompleteConnector()


def test_dcard_connector_can_handle_dcard_urls():
    connector = DcardConnector()

    assert connector.can_handle("https://www.dcard.tw/f/trending")
    assert not connector.can_handle("https://example.com/f/trending")


def test_dcard_connector_normalizes_listing_item():
    connector = DcardConnector()
    raw = {
        "id": 12345,
        "title": "Test title",
        "excerpt": "Test excerpt",
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": None,
        "comment_count": 1,
        "like_count": 2,
        "topics": [],
    }
    connector._forum_alias_by_id["12345"] = "trending"

    post = connector.normalize_item(ConnectorItem(external_id="12345", raw=raw))

    assert post.platform == "dcard"
    assert post.external_id == "12345"
    assert post.board_or_forum == "trending"


def test_connector_registry_finds_connector_by_name_and_url():
    connector = DcardConnector()
    registry = ConnectorRegistry([connector])

    assert registry.names() == ["dcard"]
    assert registry.get("dcard") is connector
    assert registry.find_for_url("https://www.dcard.tw/f/trending") is connector


def test_connector_registry_raises_for_unknown_url():
    registry = ConnectorRegistry([DcardConnector()])

    with pytest.raises(KeyError):
        registry.find_for_url("https://example.com/page")


@pytest.mark.asyncio
async def test_dcard_connector_fetch_listing_uses_http_client():
    class FakeHttpClient:
        async def get_json(self, url, **kwargs):
            assert url == "/forums/trending/posts"
            assert kwargs["params"]["popular"] == "false"
            return [
                {
                    "id": 12345,
                    "title": "Test title",
                    "excerpt": "Test excerpt",
                    "created_at": "2024-01-01T12:00:00Z",
                    "comment_count": 1,
                    "like_count": 2,
                    "topics": [],
                }
            ]

        async def close(self):
            return None

    connector = DcardConnector(http_client=FakeHttpClient())
    target = ConnectorTarget(url="https://www.dcard.tw/f/trending", label="trending")
    items = await connector.fetch_listing(target)

    assert len(items) == 1
    assert items[0].external_id == "12345"


@pytest.mark.asyncio
async def test_dcard_connector_fetch_listing_mode_sets_popular_param():
    seen_params = []

    class FakeHttpClient:
        async def get_json(self, url, **kwargs):
            seen_params.append(kwargs["params"])
            return []

        async def close(self):
            return None

    connector = DcardConnector(http_client=FakeHttpClient())
    target = ConnectorTarget(url="https://www.dcard.tw/f/trending", label="trending")

    await connector.fetch_listing(target, mode="latest")
    await connector.fetch_listing(target, mode="popular")

    assert seen_params[0]["popular"] == "false"
    assert seen_params[1]["popular"] == "true"


@pytest.mark.asyncio
async def test_dcard_connector_fetch_detail_normalizes_without_live_network():
    class FakeHttpClient:
        request_count = 1

        async def get_json(self, url, **kwargs):
            assert url == "/posts/12345"
            return {
                "id": 12345,
                "title": "Detail title",
                "excerpt": "Detail excerpt",
                "content": "Detail content",
                "created_at": "2024-01-01T12:00:00Z",
                "comment_count": 1,
                "like_count": 2,
                "topics": [],
                "forum_alias": "trending",
                "forum_name": "Trending",
                "media": [],
            }

        async def close(self):
            return None

    connector = DcardConnector(http_client=FakeHttpClient())
    item = await connector.fetch_detail(ConnectorItem(external_id="12345", raw={"id": 12345}))

    assert item is not None
    post = connector.normalize_item(item)
    assert post.content == "Detail content"
    assert post.board_or_forum == "trending"
    assert post.source_name == "dcard"
    assert post.platform == "dcard"
    assert post.external_id == "12345"
    assert post.content_hash


@pytest.mark.asyncio
async def test_dcard_connector_policy_error_is_not_swallowed():
    class FakeHttpClient:
        request_count = 1

        async def get_json(self, url, **kwargs):
            raise RateLimitedError("rate limited")

        async def close(self):
            return None

    connector = DcardConnector(http_client=FakeHttpClient())

    with pytest.raises(RateLimitedError):
        await connector.fetch_detail(ConnectorItem(external_id="12345", raw={"id": 12345}))
