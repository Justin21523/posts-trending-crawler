"""Tests for PTT connector parsing and normalization."""

import pytest

from dcard_crawler.connectors.base import ConnectorItem, ConnectorTarget
from dcard_crawler.connectors.ptt import PttConnector
from dcard_crawler.core.errors import ChallengeDetectedError

PTT_LISTING_HTML = """
<div class="r-ent">
  <div class="nrec"><span class="hl f2">爆</span></div>
  <div class="title"><a href="/bbs/Stock/M.1700000000.A.123.html">[標的] 台積電</a></div>
  <div class="meta"><div class="author">alice</div><div class="date"> 1/01</div></div>
</div>
<div class="r-ent">
  <div class="nrec">X1</div>
  <div class="title">(本文已被刪除)</div>
  <div class="meta"><div class="author">-</div><div class="date"> 1/02</div></div>
</div>
"""


PTT_ARTICLE_HTML = """
<div id="main-content">
  <div class="article-metaline"><span class="article-meta-tag">作者</span>
    <span class="article-meta-value">alice (Alice)</span></div>
  <div class="article-metaline"><span class="article-meta-tag">看板</span>
    <span class="article-meta-value">Stock</span></div>
  <div class="article-metaline"><span class="article-meta-tag">標題</span>
    <span class="article-meta-value">[標的] 台積電</span></div>
  <div class="article-metaline"><span class="article-meta-tag">時間</span>
    <span class="article-meta-value">Mon Jan  1 12:00:00 2024</span></div>
  這是文章第一段。
  這是文章第二段。
  <span class="f2">※ 發信站: 批踢踢實業坊(ptt.cc)</span>
  <div class="push"><span>推文不收</span></div>
</div>
"""


def test_ptt_listing_parser_skips_deleted_rows():
    connector = PttConnector()

    entries = connector.parse_listing(PTT_LISTING_HTML, board="Stock")

    assert len(entries) == 1
    assert entries[0].external_id == "M.1700000000.A.123"
    assert entries[0].push_count == 100
    assert entries[0].author == "alice"


def test_ptt_article_parser_removes_push_and_metadata():
    connector = PttConnector()
    entry = connector.parse_listing(PTT_LISTING_HTML, board="Stock")[0]

    raw = connector.parse_article(PTT_ARTICLE_HTML, entry)

    assert raw["author"] == "alice (Alice)"
    assert raw["published_at"].startswith("2024-01-01T12:00:00")
    assert "這是文章第一段" in raw["content"]
    assert "推文不收" not in raw["content"]
    assert "發信站" not in raw["content"]


def test_ptt_normalize_detail_uses_external_id_without_post_id():
    connector = PttConnector()
    entry = connector.parse_listing(PTT_LISTING_HTML, board="Stock")[0]
    raw = connector.parse_article(PTT_ARTICLE_HTML, entry)

    post = connector.normalize_item(ConnectorItem(entry.external_id, raw, entry.url))

    assert post.platform == "ptt"
    assert post.source_name == "ptt"
    assert post.post_id is None
    assert post.external_id == "M.1700000000.A.123"
    assert post.board_or_forum == "Stock"
    assert post.comment_count == 100


def test_ptt_push_count_variants():
    assert PttConnector.parse_push_count("爆") == 100
    assert PttConnector.parse_push_count("X1") == -1
    assert PttConnector.parse_push_count("12") == 12
    assert PttConnector.parse_push_count("") == 0


def test_ptt_over18_blocks_by_default():
    connector = PttConnector()

    with pytest.raises(ChallengeDetectedError):
        connector.parse_listing('<button>我同意，我已年滿十八歲</button>', board="Gossiping")


@pytest.mark.asyncio
async def test_ptt_over18_opt_in_uses_public_confirm_flow():
    calls = []

    class FakeHttpClient:
        request_count = 3

        async def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs.get("data")))

            class Response:
                text = PTT_LISTING_HTML

            if method == "GET" and len(calls) == 1:
                Response.text = '<button>我同意，我已年滿十八歲</button>'
            return Response()

        async def close(self):
            return None

    connector = PttConnector(
        http_client=FakeHttpClient(),
        allow_over18_public_confirm=True,
    )
    items = await connector.fetch_listing(
        ConnectorTarget(url="https://www.ptt.cc/bbs/Gossiping/index.html", label="Gossiping")
    )

    assert calls[1] == (
        "POST",
        "https://www.ptt.cc/ask/over18",
        {"from": "/bbs/Gossiping/index.html", "yes": "yes"},
    )
    assert len(items) == 1
    assert connector._confirmed_over18 is True


@pytest.mark.asyncio
async def test_ptt_fetch_listing_uses_target_page():
    class FakeHttpClient:
        request_count = 1

        async def request(self, method, url, **kwargs):
            class Response:
                text = PTT_LISTING_HTML

            assert method == "GET"
            assert url == "https://www.ptt.cc/bbs/Stock/index2.html"
            return Response()

        async def close(self):
            return None

    connector = PttConnector(http_client=FakeHttpClient())
    items = await connector.fetch_listing(
        ConnectorTarget(url="https://www.ptt.cc/bbs/Stock/index.html", label="Stock"),
        page=2,
    )

    assert len(items) == 1
