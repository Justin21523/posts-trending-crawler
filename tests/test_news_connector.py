"""Tests for News connector parsing and normalization."""

import pytest

from dcard_crawler.connectors.base import ConnectorItem
from dcard_crawler.connectors.news import NewsConnector, NewsItem
from dcard_crawler.core.errors import RateLimitedError

RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>RSS title</title>
    <link>https://news.example.com/a</link>
    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    <author>reporter@example.com</author>
    <category>政治</category>
    <description>RSS summary</description>
  </item>
</channel></rss>
"""


ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Atom title</title>
    <link href="https://news.example.com/atom-a" />
    <updated>2024-01-02T12:00:00+08:00</updated>
    <author><name>Atom Reporter</name></author>
    <category term="財經" />
    <summary>Atom summary</summary>
  </entry>
</feed>
"""


SITEMAP_XML = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://news.example.com/a</loc></url>
  <url><loc>https://news.example.com/b</loc></url>
</urlset>
"""


ARTICLE_HTML = """
<html><head>
<link rel="canonical" href="https://news.example.com/canonical-a" />
<script type="application/ld+json">
{
  "@type": "NewsArticle",
  "headline": "Article title",
  "author": {"name": "Jane"},
  "datePublished": "2024-01-03T12:00:00+08:00",
  "articleSection": "社會",
  "keywords": ["台灣", "新聞"],
  "articleBody": "Article body content long enough for validation."
}
</script>
</head><body><article>Fallback article text</article></body></html>
"""


FALLBACK_HTML = """
<html><head>
<title>Fallback title</title>
<link rel="canonical" href="https://news.example.com/fallback" />
<meta property="og:title" content="OG title" />
<meta name="description" content="Fallback summary" />
<meta name="author" content="Fallback Reporter" />
<meta property="article:published_time" content="2024-01-04T12:00:00+08:00" />
<meta property="article:section" content="生活" />
<meta name="keywords" content="生活,台北" />
</head><body><article>Fallback body content long enough.</article></body></html>
"""


def test_news_parse_rss_feed():
    connector = NewsConnector(source_name="demo")

    items = connector.parse_feed(RSS_XML)

    assert len(items) == 1
    assert items[0].title == "RSS title"
    assert items[0].url == "https://news.example.com/a"
    assert items[0].tags == ["政治"]
    assert items[0].published_at.startswith("2024-01-01T12:00:00")


def test_news_parse_atom_feed():
    connector = NewsConnector(source_name="demo")

    items = connector.parse_feed(ATOM_XML)

    assert len(items) == 1
    assert items[0].title == "Atom title"
    assert items[0].author == "Atom Reporter"
    assert items[0].tags == ["財經"]


def test_news_parse_sitemap_limit():
    connector = NewsConnector(source_name="demo")

    items = connector.parse_sitemap(SITEMAP_XML, max_articles=1)

    assert len(items) == 1
    assert items[0].url == "https://news.example.com/a"


def test_news_parse_article_json_ld():
    connector = NewsConnector(source_name="demo")
    fallback = NewsItem(url="https://news.example.com/a", title="Feed title", source_name="demo")

    article = connector.parse_article(ARTICLE_HTML, fallback=fallback)

    assert article.title == "Article title"
    assert article.author == "Jane"
    assert article.section == "社會"
    assert article.tags == ["台灣", "新聞"]
    assert article.canonical_url == "https://news.example.com/canonical-a"


def test_news_parse_article_fallback_meta():
    connector = NewsConnector(source_name="demo")

    article = connector.parse_article(
        FALLBACK_HTML,
        fallback=NewsItem(url="https://news.example.com/fallback", source_name="demo"),
    )

    assert article.title == "OG title"
    assert article.author == "Fallback Reporter"
    assert article.section == "生活"
    assert "Fallback body content" in article.content


def test_news_normalize_item():
    connector = NewsConnector(source_name="demo")
    article = connector.parse_article(
        ARTICLE_HTML,
        fallback=NewsItem(url="https://news.example.com/a", source_name="demo"),
    )

    post = connector.normalize_item(ConnectorItem(article.external_id, article, article.url))

    assert post.platform == "news"
    assert post.source_type == "news"
    assert post.source_name == "demo"
    assert post.board_or_forum == "社會"
    assert post.content_hash


@pytest.mark.asyncio
async def test_news_connector_policy_error_not_swallowed():
    class FakeHttpClient:
        request_count = 1

        async def request(self, method, url, **kwargs):
            raise RateLimitedError("blocked")

        async def close(self):
            return None

    connector = NewsConnector(http_client=FakeHttpClient(), source_name="demo")

    with pytest.raises(RateLimitedError):
        await connector.fetch_detail(
            ConnectorItem("id", NewsItem(url="https://news.example.com/a"), "https://news.example.com/a")
        )
