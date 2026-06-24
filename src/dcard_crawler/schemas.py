"""Pydantic schemas for Dcard API responses and internal models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PostListItem(BaseModel):
    """Minimal post data from listing endpoint."""

    id: int
    title: str
    excerpt: str = ""
    created_at: str
    updated_at: str | None = None
    comment_count: int = 0
    like_count: int = 0
    school: str | None = None
    department: str | None = None
    anonymous_school: bool = False
    anonymous_department: bool = False
    with_nickname: bool = False
    nsfw: bool = False
    gender: str | None = None
    topics: list[dict[str, Any]] = Field(default_factory=list)


class PostDetail(PostListItem):
    """Full post data from detail endpoint."""

    content: str = ""
    forum_alias: str | None = None
    forum_name: str | None = None
    media: list[dict[str, Any]] = Field(default_factory=list)
    preview: str | None = None
    url: str | None = None


class NormalizedPost(BaseModel):
    """Normalized post ready for storage."""

    source_id: int | None = None
    source_name: str = "dcard"
    source_type: str = "forum"
    platform: str = "dcard"
    external_id: str | None = None
    post_id: int
    forum_alias: str | None = None
    forum_name: str | None = None
    board_or_forum: str | None = None
    title: str
    author_display: str | None = None
    excerpt: str = ""
    content: str = ""
    published_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0
    topics: list[dict[str, Any]] = Field(default_factory=list)
    media_meta: list[dict[str, Any]] = Field(default_factory=list)
    school: str | None = None
    department: str | None = None
    gender: str | None = None
    anonymous_school: bool = False
    anonymous_department: bool = False
    with_nickname: bool = False
    nsfw: bool = False
    url: str | None = None
    canonical_url: str | None = None
    crawl_source: str = "api"
    crawled_at: datetime = Field(default_factory=datetime.now)
    raw_json: dict[str, Any] = Field(default_factory=dict)
    raw_html_path: str | None = None
    content_hash: str | None = None
    language: str | None = "zh-TW"

    def model_post_init(self, __context: Any) -> None:
        """Fill compatibility defaults after validation."""
        if self.external_id is None:
            self.external_id = str(self.post_id)
        if self.board_or_forum is None:
            self.board_or_forum = self.forum_alias
        if self.published_at is None:
            self.published_at = self.created_at


class Checkpoint(BaseModel):
    """Checkpoint state for resuming crawls."""

    forum_alias: str
    last_post_id: int | None = None
    last_success_at: str | None = None
    total_fetched: int = 0
    popular_mode: bool = False


class DiscoveredEndpoint(BaseModel):
    """Discovered API endpoint from browser monitoring."""

    url_pattern: str
    method: str = "GET"
    status: str = "active"
    discovered_at: datetime = Field(default_factory=datetime.now)
    sample_response_keys: list[str] = Field(default_factory=list)
