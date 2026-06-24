"""News connector for RSS, sitemap, and public article pages."""

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.core.html_utils import extract_canonical_url
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.text_utils import content_hash, normalize_whitespace
from dcard_crawler.schemas import NormalizedPost


@dataclass
class NewsItem:
    """Parsed news feed or article data."""

    url: str
    title: str = ""
    source_name: str = "news"
    published_at: str | None = None
    author: str | None = None
    summary: str = ""
    content: str = ""
    section: str | None = None
    tags: list[str] = field(default_factory=list)
    canonical_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def external_id(self) -> str:
        """Stable ID based on canonical URL or URL."""
        value = self.canonical_url or self.url
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


class NewsConnector(BaseConnector):
    """Connector for public RSS feeds, sitemaps, and article pages."""

    name = "news"
    source_type = "news"
    allowed_domains: tuple[str, ...] = ()

    def __init__(
        self,
        http_client: CrawlerHttpClient | None = None,
        *,
        source_name: str = "news",
    ):
        self.http_client = http_client or CrawlerHttpClient()
        self.source_name = source_name

    @property
    def request_count(self) -> int:
        """Return connector request count when supported by the HTTP client."""
        return int(getattr(self.http_client, "request_count", 0))

    def can_handle(self, url: str) -> bool:
        """Return whether this connector can handle a news URL."""
        return urlparse(url).scheme in {"http", "https"}

    async def discover_targets(self) -> list[ConnectorTarget]:
        """News targets are user-supplied via CLI."""
        return []

    async def fetch_listing(
        self,
        target: ConnectorTarget,
        max_articles: int | None = None,
        **kwargs,
    ) -> list[ConnectorItem]:
        """Fetch RSS or sitemap listing items."""
        target_type = (target.metadata or {}).get("target_type", "rss")
        text = await self._get_text(target.url)
        if target_type == "sitemap":
            items = self.parse_sitemap(text, max_articles=max_articles)
        elif target_type == "article":
            items = [NewsItem(url=target.url, source_name=self.source_name)]
        else:
            items = self.parse_feed(text)

        if max_articles is not None:
            items = items[:max_articles]
        return [self.parse_item(item) for item in items]

    async def fetch_detail(self, item: ConnectorItem) -> ConnectorItem | None:
        """Fetch and parse one public article page."""
        if not item.url:
            return None
        html = await self._get_text(item.url)
        feed_item = item.raw if isinstance(item.raw, NewsItem) else NewsItem(url=item.url)
        article = self.parse_article(html, fallback=feed_item)
        return ConnectorItem(external_id=article.external_id, raw=article, url=article.url)

    def parse_item(self, raw) -> ConnectorItem:
        """Parse raw news item into connector item."""
        if isinstance(raw, NewsItem):
            return ConnectorItem(external_id=raw.external_id, raw=raw, url=raw.url)
        item = NewsItem(url=raw["url"], title=raw.get("title", ""), source_name=self.source_name)
        return ConnectorItem(external_id=item.external_id, raw=item, url=item.url)

    def normalize_item(self, item: ConnectorItem) -> NormalizedPost:
        """Normalize news item into shared post schema."""
        raw = item.raw if isinstance(item.raw, NewsItem) else NewsItem(url=item.url or "")
        canonical_url = raw.canonical_url or raw.url
        content = raw.content or raw.summary
        return NormalizedPost(
            source_name=raw.source_name or self.source_name,
            source_type="news",
            platform="news",
            external_id=raw.external_id,
            post_id=None,
            board_or_forum=raw.section,
            title=raw.title,
            author_display=raw.author,
            excerpt=raw.summary,
            content=content,
            published_at=raw.published_at,
            created_at=raw.published_at,
            topics=[{"name": tag} for tag in raw.tags],
            url=raw.url,
            canonical_url=canonical_url,
            crawl_source="rss" if not raw.content else "html",
            raw_json=raw.raw,
            content_hash=content_hash(raw.title, content, canonical_url),
        )

    def parse_feed(self, xml_text: str) -> list[NewsItem]:
        """Parse RSS or Atom feed XML."""
        root = ET.fromstring(xml_text.encode("utf-8"))
        if self._strip_namespace(root.tag) == "feed":
            return self._parse_atom(root)
        return self._parse_rss(root)

    def parse_sitemap(self, xml_text: str, max_articles: int | None = None) -> list[NewsItem]:
        """Parse sitemap URL XML."""
        root = ET.fromstring(xml_text.encode("utf-8"))
        items = []
        for loc in root.findall(".//{*}loc"):
            if loc.text:
                items.append(
                    NewsItem(
                        url=normalize_whitespace(loc.text),
                        source_name=self.source_name,
                    )
                )
            if max_articles is not None and len(items) >= max_articles:
                break
        return items

    def parse_article(self, html: str, fallback: NewsItem | None = None) -> NewsItem:
        """Parse public article HTML with JSON-LD and meta fallback."""
        fallback = fallback or NewsItem(url="")
        soup = BeautifulSoup(html or "", "lxml")
        json_ld = self._json_ld_article(soup)
        canonical = extract_canonical_url(html) or fallback.canonical_url or fallback.url
        meta = self._meta_article(soup)
        content = json_ld.get("articleBody") or self._article_text(soup)
        tags = self._tags(json_ld, meta, fallback)
        return NewsItem(
            url=fallback.url or canonical,
            title=json_ld.get("headline") or meta.get("title") or fallback.title,
            source_name=fallback.source_name or self.source_name,
            published_at=self._date(json_ld.get("datePublished") or meta.get("published_at"))
            or fallback.published_at,
            author=self._author(json_ld.get("author")) or meta.get("author") or fallback.author,
            summary=meta.get("summary") or fallback.summary,
            content=normalize_whitespace(content),
            section=json_ld.get("articleSection") or meta.get("section") or fallback.section,
            tags=tags,
            canonical_url=canonical,
            raw={"json_ld": json_ld, "meta": meta, **fallback.raw},
        )

    async def close(self) -> None:
        """Close connector resources."""
        await self.http_client.close()

    async def _get_text(self, url: str) -> str:
        response = await self.http_client.request("GET", url)
        return response.text

    def _parse_rss(self, root) -> list[NewsItem]:
        items = []
        for node in root.findall(".//item"):
            categories = [
                normalize_whitespace(cat.text)
                for cat in node.findall("category")
                if cat.text
            ]
            items.append(
                NewsItem(
                    url=self._text(node, "link"),
                    title=self._text(node, "title"),
                    source_name=self.source_name,
                    published_at=self._date(self._text(node, "pubDate")),
                    author=self._text(node, "author") or self._text(node, "{*}creator"),
                    summary=self._text(node, "description"),
                    tags=categories,
                    raw={"feed_type": "rss"},
                )
            )
        return [item for item in items if item.url]

    def _parse_atom(self, root) -> list[NewsItem]:
        items = []
        for node in root.findall("{*}entry"):
            link = node.find("{*}link")
            href = link.get("href") if link is not None else ""
            categories = [cat.get("term") for cat in node.findall("{*}category") if cat.get("term")]
            author = node.find("{*}author/{*}name")
            items.append(
                NewsItem(
                    url=href,
                    title=self._text(node, "{*}title"),
                    source_name=self.source_name,
                    published_at=self._date(
                        self._text(node, "{*}updated") or self._text(node, "{*}published")
                    ),
                    author=normalize_whitespace(author.text) if author is not None else None,
                    summary=self._text(node, "{*}summary"),
                    tags=categories,
                    raw={"feed_type": "atom"},
                )
            )
        return [item for item in items if item.url]

    @staticmethod
    def _json_ld_article(soup: BeautifulSoup) -> dict:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            candidates = data if isinstance(data, list) else [data]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("@graph"):
                    candidates.extend(candidate["@graph"])
                if not isinstance(candidate, dict):
                    continue
                article_type = candidate.get("@type")
                if article_type in {"NewsArticle", "Article"}:
                    return candidate
        return {}

    @staticmethod
    def _meta_article(soup: BeautifulSoup) -> dict:
        def content(*names: str) -> str:
            for name in names:
                tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
                if tag and tag.get("content"):
                    return normalize_whitespace(tag["content"])
            return ""

        title_text = normalize_whitespace(soup.title.string if soup.title else "")
        return {
            "title": content("og:title", "twitter:title") or title_text,
            "summary": content("description", "og:description"),
            "author": content("author", "article:author"),
            "published_at": content("article:published_time"),
            "section": content("article:section"),
            "keywords": content("keywords", "news_keywords"),
        }

    @staticmethod
    def _article_text(soup: BeautifulSoup) -> str:
        article = soup.find("article") or soup.find("main") or soup.body
        if not article:
            return ""
        for tag in article(["script", "style", "noscript"]):
            tag.decompose()
        return normalize_whitespace(article.get_text(" "))

    @staticmethod
    def _tags(json_ld: dict, meta: dict, fallback: NewsItem) -> list[str]:
        keywords = json_ld.get("keywords") or meta.get("keywords")
        if isinstance(keywords, str):
            tags = [normalize_whitespace(tag) for tag in keywords.split(",")]
        elif isinstance(keywords, list):
            tags = [normalize_whitespace(str(tag)) for tag in keywords]
        else:
            tags = []
        return [tag for tag in [*fallback.tags, *tags] if tag]

    @staticmethod
    def _author(value) -> str | None:
        if isinstance(value, str):
            return normalize_whitespace(value)
        if isinstance(value, dict):
            return normalize_whitespace(value.get("name"))
        if isinstance(value, list) and value:
            return NewsConnector._author(value[0])
        return None

    @staticmethod
    def _date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return date_parser.parse(value).isoformat()
        except Exception:
            return normalize_whitespace(value)

    @staticmethod
    def _text(node, name: str) -> str:
        found = node.find(name)
        return normalize_whitespace(found.text) if found is not None and found.text else ""

    @staticmethod
    def _strip_namespace(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag
