"""Parser for normalizing raw Dcard API data into storage-ready format."""

from datetime import datetime

from dcard_crawler.schemas import NormalizedPost, PostDetail, PostListItem


class PostParser:
    """Parser for converting API responses to normalized format."""

    def normalize_list_item(self, item: PostListItem, forum_alias: str) -> NormalizedPost:
        """Normalize a post from listing endpoint.

        Args:
            item: PostListItem from API
            forum_alias: Forum alias for context

        Returns:
            NormalizedPost ready for storage
        """
        url = f"https://www.dcard.tw/f/{forum_alias}/p/{item.id}"

        return NormalizedPost(
            post_id=item.id,
            forum_alias=forum_alias,
            forum_name=None,  # Not available in listing
            title=item.title,
            excerpt=item.excerpt,
            content="",  # Not available in listing
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
            crawl_source="api",
            crawled_at=datetime.now(),
            raw_json=item.model_dump(),
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

        return NormalizedPost(
            post_id=detail.id,
            forum_alias=detail.forum_alias,
            forum_name=detail.forum_name,
            title=detail.title,
            excerpt=detail.excerpt,
            content=detail.content,
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
            crawl_source="api",
            crawled_at=datetime.now(),
            raw_json=detail.model_dump(),
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

        return normalized
