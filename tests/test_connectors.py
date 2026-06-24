"""Tests for connector contracts and Dcard connector behavior."""

import pytest

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.connectors.dcard import DcardConnector


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
