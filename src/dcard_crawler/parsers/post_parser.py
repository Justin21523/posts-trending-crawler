"""Parser for normalizing raw Dcard API data into storage-ready format."""

import hashlib
from datetime import datetime

from dcard_crawler.schemas import NormalizedPost, PostDetail, PostListItem


class PostParser:
    """Parser for converting API responses to normalized format."""

    platform = "dcard"
    source_name = "dcard"
    source_type = "forum"

    def normalize_list_item(self, item: PostListItem, forum_alias: str) -> NormalizedPost:
        """Normalize a post from listing endpoint.

        Args:
            item: PostListItem from API
            forum_alias: Forum alias for context

        Returns:
            NormalizedPost ready for storage
        """
        url = f"https://www.dcard.tw/f/{forum_alias}/p/{item.id}"
        text_for_hash = f"{item.title}\n{item.excerpt}\n{url}"

        return NormalizedPost(
            source_name=self.source_name,
            source_type=self.source_type,
            platform=self.platform,
            external_id=str(item.id),
            post_id=item.id,
            forum_alias=forum_alias,
            forum_name=None,  # Not available in listing
            board_or_forum=forum_alias,
            title=item.title,
            excerpt=item.excerpt,
            content="",  # Not available in listing
            published_at=item.created_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
            like_count=item.like_count,
            comment_count=item.comment_count,
            topics=item.topics,
            media_meta=[],  # Not available in listing
            school=item.school,
            department=item.department,
            gender=item.gender,
            anonymous_school=item.anonymous_school,
            anonymous_department=item.anonymous_department,
            with_nickname=item.with_nickname,
            nsfw=item.nsfw,
            url=url,
            canonical_url=url,
            crawl_source="api",
            crawled_at=datetime.now(),
            raw_json=item.model_dump(),
            content_hash=self._content_hash(text_for_hash),
        )

    def normalize_detail(self, detail: PostDetail) -> NormalizedPost:
        """Normalize a post from detail endpoint.

        Args:
            detail: PostDetail from API

        Returns:
            NormalizedPost ready for storage
        """
        # Build URL if not provided
        url = detail.url
        if not url and detail.forum_alias:
            url = f"https://www.dcard.tw/f/{detail.forum_alias}/p/{detail.id}"

        # Extract media metadata
        media_meta = []
        for media in detail.media:
            media_info = {
                "type": media.get("type"),
                "url": media.get("url"),
                "width": media.get("width"),
                "height": media.get("height"),
            }
            media_meta.append(media_info)

        text_for_hash = f"{detail.title}\n{detail.content or detail.excerpt}\n{url or detail.id}"

        return NormalizedPost(
            source_name=self.source_name,
            source_type=self.source_type,
            platform=self.platform,
            external_id=str(detail.id),
            post_id=detail.id,
            forum_alias=detail.forum_alias,
            forum_name=detail.forum_name,
            board_or_forum=detail.forum_alias,
            title=detail.title,
            excerpt=detail.excerpt,
            content=detail.content,
            published_at=detail.created_at,
            created_at=detail.created_at,
            updated_at=detail.updated_at,
            like_count=detail.like_count,
            comment_count=detail.comment_count,
            topics=detail.topics,
            media_meta=media_meta,
            school=detail.school,
            department=detail.department,
            gender=detail.gender,
            anonymous_school=detail.anonymous_school,
            anonymous_department=detail.anonymous_department,
            with_nickname=detail.with_nickname,
            nsfw=detail.nsfw,
            url=url,
            canonical_url=url,
            crawl_source="api",
            crawled_at=datetime.now(),
            raw_json=detail.model_dump(),
            content_hash=self._content_hash(text_for_hash),
        )

    def merge_list_with_detail(
        self, list_item: PostListItem, detail: PostDetail, forum_alias: str
    ) -> NormalizedPost:
        """Merge listing data with detail data, preferring detail for completeness.

        Args:
            list_item: PostListItem from listing API
            detail: PostDetail from detail API
            forum_alias: Forum alias

        Returns:
            Merged NormalizedPost
        """
        # Use detail as primary source since it's more complete
        normalized = self.normalize_detail(detail)

        # Fill in any missing fields from list item
        if not normalized.forum_alias:
            normalized.forum_alias = forum_alias
        if not normalized.board_or_forum:
            normalized.board_or_forum = forum_alias

        return normalized

    @staticmethod
    def _content_hash(text: str) -> str:
        """Create a deterministic content hash for duplicate detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
