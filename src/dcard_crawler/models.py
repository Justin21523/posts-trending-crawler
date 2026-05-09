"""SQLAlchemy ORM model for posts."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Text

from dcard_crawler.database import Base


class Post(Base):
    """ORM model for storing Dcard post data."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, unique=True, nullable=False, index=True)
    forum_alias = Column(String(100), nullable=True)
    forum_name = Column(String(200), nullable=True)
    title = Column(String(500), nullable=False)
    excerpt = Column(Text, nullable=True, default="")
    content = Column(Text, nullable=True, default="")
    created_at = Column(String(50), nullable=True)
    updated_at = Column(String(50), nullable=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    topics = Column(JSON, nullable=True, default=list)
    media_meta = Column(JSON, nullable=True, default=list)
    school = Column(String(100), nullable=True)
    department = Column(String(200), nullable=True)
    gender = Column(String(50), nullable=True)
    anonymous_school = Column(Boolean, default=False)
    anonymous_department = Column(Boolean, default=False)
    with_nickname = Column(Boolean, default=False)
    nsfw = Column(Boolean, default=False)
    url = Column(String(500), nullable=True)
    crawl_source = Column(String(50), default="api")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False)
    raw_json = Column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("idx_post_id", "post_id"),
        Index("idx_forum_created", "forum_alias", "created_at"),
        Index("idx_crawled_at", "crawled_at"),
    )

    def __repr__(self):
        return f"<Post post_id={self.post_id} title='{self.title[:50]}'>"
