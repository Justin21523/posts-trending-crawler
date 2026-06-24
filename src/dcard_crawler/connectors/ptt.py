"""PTT connector for public board/article pages."""

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from dcard_crawler.connectors.base import BaseConnector, ConnectorItem, ConnectorTarget
from dcard_crawler.core.errors import ChallengeDetectedError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.text_utils import content_hash, normalize_whitespace
from dcard_crawler.schemas import NormalizedPost


@dataclass(frozen=True)
class PttListingEntry:
    """Parsed PTT listing metadata."""

    external_id: str
    title: str
    author: str | None
    date_text: str | None
    push_count: int
    url: str
    board: str


class PttConnector(BaseConnector):
    """Connector for public PTT board and article pages."""

    name = "ptt"
    source_type = "forum"
    allowed_domains = ("www.ptt.cc",)

    def __init__(
        self,
        http_client: CrawlerHttpClient | None = None,
        *,
        default_board: str = "Stock",
        allow_over18_public_confirm: bool = False,
    ):
        self.http_client = http_client or CrawlerHttpClient(base_url="https://www.ptt.cc")
        self.default_board = default_board
        self.allow_over18_public_confirm = allow_over18_public_confirm
        self._confirmed_over18 = False

    @property
    def request_count(self) -> int:
        """Return connector request count when supported by the HTTP client."""
        return int(getattr(self.http_client, "request_count", 0))

    def can_handle(self, url: str) -> bool:
        """Return whether this connector handles the URL."""
        return urlparse(url).netloc.lower() in self.allowed_domains

    async def discover_targets(self) -> list[ConnectorTarget]:
        """Return the configured default PTT board target."""
        return [self.board_target(self.default_board)]

    @staticmethod
    def board_target(board: str, page: int | None = None) -> ConnectorTarget:
        """Build a board target for index or explicit index page."""
        path = f"/bbs/{board}/index.html" if page is None else f"/bbs/{board}/index{page}.html"
        return ConnectorTarget(url=f"https://www.ptt.cc{path}", label=board)

    async def fetch_listing(
        self,
        target: ConnectorTarget,
        page: int | None = None,
        **kwargs,
    ) -> list[ConnectorItem]:
        """Fetch and parse a PTT board listing page."""
        url = target.url if page in {None, 1} else self.board_target(target.label, page).url
        html = await self._get_text(url)
        entries = self.parse_listing(html, board=target.label)
        return [self.parse_item(entry) for entry in entries]

    async def fetch_detail(self, item: ConnectorItem) -> ConnectorItem | None:
        """Fetch and parse one PTT article."""
        if not item.url:
            return None
        html = await self._get_text(item.url)
        raw = self.parse_article(html, item.raw)
        return ConnectorItem(external_id=item.external_id, raw=raw, url=item.url)

    def parse_item(self, raw) -> ConnectorItem:
        """Parse listing metadata into a connector item."""
        if isinstance(raw, PttListingEntry):
            return ConnectorItem(external_id=raw.external_id, raw=raw, url=raw.url)
        return ConnectorItem(external_id=str(raw["external_id"]), raw=raw, url=raw.get("url"))

    def normalize_item(self, item: ConnectorItem) -> NormalizedPost:
        """Normalize PTT listing/detail data into shared post schema."""
        raw = item.raw
        if isinstance(raw, PttListingEntry):
            data = raw.__dict__
            content = ""
        else:
            data = raw
            content = data.get("content", "")

        published_at = data.get("published_at") or self._parse_listing_date(data.get("date_text"))
        url = data.get("url") or item.url
        board = data.get("board") or self._board_from_url(url)
        text_hash = content_hash(data.get("title"), content, url)
        return NormalizedPost(
            source_name="ptt",
            source_type="forum",
            platform="ptt",
            external_id=str(data["external_id"]),
            post_id=None,
            board_or_forum=board,
            title=data.get("title") or "",
            author_display=data.get("author"),
            excerpt=normalize_whitespace(content[:200]),
            content=content,
            published_at=published_at,
            created_at=published_at,
            comment_count=int(data.get("push_count") or 0),
            url=url,
            canonical_url=url,
            crawl_source="html",
            raw_json=self._json_safe_raw(data),
            content_hash=text_hash,
        )

    def parse_listing(self, html: str, board: str) -> list[PttListingEntry]:
        """Parse PTT board listing HTML."""
        self._raise_if_over18(html)
        soup = BeautifulSoup(html or "", "lxml")
        entries = []
        for row in soup.select(".r-ent"):
            title_tag = row.select_one(".title a")
            if not title_tag:
                continue
            href = title_tag.get("href")
            if not href:
                continue
            url = urljoin("https://www.ptt.cc", href)
            external_id = href.rsplit("/", 1)[-1].removesuffix(".html")
            entries.append(
                PttListingEntry(
                    external_id=external_id,
                    title=normalize_whitespace(title_tag.get_text(" ")),
                    author=normalize_whitespace(row.select_one(".author").get_text(" "))
                    if row.select_one(".author")
                    else None,
                    date_text=normalize_whitespace(row.select_one(".date").get_text(" "))
                    if row.select_one(".date")
                    else None,
                    push_count=self.parse_push_count(
                        normalize_whitespace(row.select_one(".nrec").get_text(" "))
                        if row.select_one(".nrec")
                        else ""
                    ),
                    url=url,
                    board=board,
                )
            )
        return entries

    def parse_article(self, html: str, listing_raw) -> dict:
        """Parse one PTT article page."""
        self._raise_if_over18(html)
        soup = BeautifulSoup(html or "", "lxml")
        main = soup.select_one("#main-content")
        if main is None:
            raise ValueError("PTT article missing #main-content")

        metadata = self._article_metadata(main)
        for tag in main.select(".article-metaline, .article-metaline-right, .push"):
            tag.decompose()
        for tag in main.find_all("span", class_="f2"):
            tag.decompose()
        content = normalize_whitespace(main.get_text("\n"))

        listing = listing_raw.__dict__ if isinstance(listing_raw, PttListingEntry) else listing_raw
        url = listing.get("url")
        return {
            **listing,
            "title": metadata.get("title") or listing.get("title"),
            "author": metadata.get("author") or listing.get("author"),
            "published_at": metadata.get("published_at"),
            "content": content,
            "url": url,
        }

    @staticmethod
    def parse_push_count(text: str) -> int:
        """Parse PTT push count text."""
        text = normalize_whitespace(text)
        if not text:
            return 0
        if text == "爆":
            return 100
        if text.startswith("X"):
            return -int(text[1:] or "0")
        return int(text) if re.fullmatch(r"-?\d+", text) else 0

    async def close(self) -> None:
        """Close connector resources."""
        await self.http_client.close()

    async def _get_text(self, url: str) -> str:
        response = await self.http_client.request("GET", url)
        html = response.text
        if (
            self._is_over18_page(html)
            and self.allow_over18_public_confirm
            and not self._confirmed_over18
        ):
            await self._confirm_over18(url)
            response = await self.http_client.request("GET", url)
            html = response.text
        return html

    def _raise_if_over18(self, html: str) -> None:
        if self._is_over18_page(html):
            raise ChallengeDetectedError("PTT over18 confirmation required")

    async def _confirm_over18(self, url: str) -> None:
        parsed = urlparse(url)
        await self.http_client.request(
            "POST",
            "https://www.ptt.cc/ask/over18",
            data={"from": parsed.path, "yes": "yes"},
        )
        self._confirmed_over18 = True

    @staticmethod
    def _is_over18_page(html: str) -> bool:
        return "我同意，我已年滿十八歲" in html or "over18" in html.lower()

    @staticmethod
    def _article_metadata(main) -> dict:
        values = [tag.get_text(" ", strip=True) for tag in main.select(".article-meta-value")]
        published_at = None
        if len(values) >= 4:
            try:
                published_at = date_parser.parse(values[3]).isoformat()
            except Exception:
                published_at = values[3]
        return {
            "author": values[0] if len(values) > 0 else None,
            "title": values[2] if len(values) > 2 else None,
            "published_at": published_at,
        }

    @staticmethod
    def _parse_listing_date(date_text: str | None) -> str | None:
        if not date_text:
            return None
        return normalize_whitespace(date_text)

    @staticmethod
    def _board_from_url(url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"/bbs/([^/]+)/", url)
        return match.group(1) if match else None

    @staticmethod
    def _json_safe_raw(data: dict) -> dict:
        json_types = (str, int, bool, type(None))
        return {key: value for key, value in data.items() if isinstance(value, json_types)}
