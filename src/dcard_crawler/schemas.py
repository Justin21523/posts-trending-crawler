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

    post_id: int
    forum_alias: str | None = None
    forum_name: str | None = None
    title: str
    excerpt: str = ""
    content: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    like_count: int = 0
    comment_count: int = 0
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
    crawl_source: str = "api"
    crawled_at: datetime = Field(default_factory=datetime.now)
    raw_json: dict[str, Any] = Field(default_factory=dict)


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
