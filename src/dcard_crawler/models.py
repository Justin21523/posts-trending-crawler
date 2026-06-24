"""SQLAlchemy ORM models for crawl sources, jobs, posts, and metrics."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from dcard_crawler.database import Base


class Source(Base):
    """Public data source such as Dcard, PTT, RSS, or sitemap."""

    __tablename__ = "sources"

    # 中文註解：來源表是多平台資料的根，後續 PTT/新聞會共用。
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    source_type = Column(String(50), nullable=False, default="forum")
    base_url = Column(String(500), nullable=True)
    robots_url = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Source name={self.name} type={self.source_type}>"


class CrawlJob(Base):
    """Track one crawl run and its outcome."""

    __tablename__ = "crawl_jobs"

    # 中文註解：job 記錄每次 crawl 的統計與錯誤，支援 provenance。
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    job_type = Column(String(100), nullable=False)
    target_url = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="running")
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    request_count = Column(Integer, default=0, nullable=False)
    item_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("idx_crawl_jobs_source_status", "source_id", "status"),
        Index("idx_crawl_jobs_started", "started_at"),
    )

    def __repr__(self):
        return f"<CrawlJob source_id={self.source_id} status={self.status}>"


class Post(Base):
    """ORM model for storing normalized public posts/articles."""

    __tablename__ = "posts"

    # 中文註解：新唯一鍵是 source_id + external_id，post_id 僅保留給 Dcard 相容。
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    external_id = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False, index=True)

    # Dcard legacy compatibility fields
    post_id = Column(Integer, nullable=True, index=True)
    forum_alias = Column(String(100), nullable=True)
    forum_name = Column(String(200), nullable=True)

    # 中文註解：通用內容欄位供論壇文章與新聞文章共用。
    board_or_forum = Column(String(200), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    author_display = Column(String(200), nullable=True)
    excerpt = Column(Text, nullable=True, default="")
    content = Column(Text, nullable=True, default="")
    url = Column(String(1000), nullable=True)
    canonical_url = Column(String(1000), nullable=True)
    published_at = Column(String(50), nullable=True, index=True)

    # Legacy Dcard timestamp names kept for existing CLI/export compatibility.
    created_at = Column(String(50), nullable=True)
    updated_at = Column(String(50), nullable=True)

    # 中文註解：跨平台 engagement 指標，缺值以 0 保存。
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    topics = Column(JSON, nullable=True, default=list)
    media_meta = Column(JSON, nullable=True, default=list)

    # Dcard public author metadata kept for backward compatibility.
    school = Column(String(100), nullable=True)
    department = Column(String(200), nullable=True)
    gender = Column(String(50), nullable=True)
    anonymous_school = Column(Boolean, default=False)
    anonymous_department = Column(Boolean, default=False)
    with_nickname = Column(Boolean, default=False)
    nsfw = Column(Boolean, default=False)

    # 中文註解：raw/provenance 欄位保留原始資料與內容指紋，方便去重與追蹤。
    crawl_source = Column(String(50), default="api")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False)
    raw_json = Column(JSON, nullable=True, default=dict)
    raw_html_path = Column(String(1000), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    language = Column(String(20), nullable=True, default="zh-TW")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_posts_source_external_id"),
        Index("idx_post_id", "post_id"),
        Index("idx_forum_created", "forum_alias", "created_at"),
        Index("idx_platform_board_published", "platform", "board_or_forum", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
    )

    def __repr__(self):
        return f"<Post platform={self.platform} external_id={self.external_id}>"


class PostMetric(Base):
    """Time-series metric captured for a post."""

    __tablename__ = "post_metrics"

    # 中文註解：指標表讓後續趨勢分析可以保存不同時間點的數值。
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Integer, nullable=False, default=0)
    captured_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_post_metrics_post_metric", "post_id", "metric_name"),
        Index("idx_post_metrics_captured", "captured_at"),
    )

    def __repr__(self):
        return f"<PostMetric post_id={self.post_id} {self.metric_name}={self.metric_value}>"
