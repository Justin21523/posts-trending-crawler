"""API request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database_ready: bool


class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str | None = None
    robots_url: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class PostResponse(BaseModel):
    id: int
    source: str
    source_id: int
    platform: str
    external_id: str
    post_id: int | None = None
    board_or_forum: str | None = None
    title: str
    excerpt: str | None = None
    content: str | None = None
    published_at: str | None = None
    created_at: str | None = None
    crawled_at: datetime
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0
    url: str | None = None
    canonical_url: str | None = None
    content_hash: str | None = None


class CrawlJobResponse(BaseModel):
    id: int
    source: str
    source_id: int
    job_type: str
    target_url: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    error_category: str | None = None
    error_reason: str | None = None
    request_count: int
    item_count: int


class ReportSummary(BaseModel):
    path: str
    report_type: str
    platform: str | None = None
    source: str | None = None
    generated_at: str | None = None
    job_id: int | None = None
    status: str | None = None


class DashboardSummary(BaseModel):
    counts: dict[str, int]
    recent_jobs: list[CrawlJobResponse]
    recent_reports: list[ReportSummary]
    platforms: dict[str, int]
    health: HealthResponse


class VerifyDcardRequest(BaseModel):
    forum: str = "trending"
    mode: str = Field(default="latest", pattern="^(latest|popular)$")
    max_posts: int = Field(default=5, ge=1, le=10)


class VerifyPttRequest(BaseModel):
    board: str = "Stock"
    max_pages: int = Field(default=1, ge=1, le=2)
    max_posts: int = Field(default=5, ge=1, le=10)
    allow_robots_unavailable: bool = False
    allow_over18_public_confirm: bool = False


class VerifyNewsRssRequest(BaseModel):
    source_name: str = "cna-technology"
    feed_url: str = "https://feeds.feedburner.com/rsscna/technology"
    max_articles: int = Field(default=5, ge=1, le=10)


class DiagnosticsDcardRequest(BaseModel):
    forum: str = "trending"
    sample_post_id: int | None = None


class VerifyResponse(BaseModel):
    platform: str
    source: str
    job_id: int | None = None
    status: str | None = None
    quality_status: str | None = None
    report_path: str
    stats: dict[str, Any]


class DiagnosticsResponse(BaseModel):
    platform: str = "dcard"
    forum: str
    report_path: str
    summary: dict[str, Any]
    endpoints: list[dict[str, Any]]
