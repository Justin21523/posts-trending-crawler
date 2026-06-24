"""Repository for post persistence operations."""


from loguru import logger
from sqlalchemy import select

from dcard_crawler.database import get_session
from dcard_crawler.models import Post
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost


class PostRepository:
    """Database repository for post CRUD operations."""

    def __init__(self, source_repository: SourceRepository | None = None):
        self.source_repository = source_repository or SourceRepository()

    def upsert(self, post: NormalizedPost) -> bool:
        """Insert or update a post record.

        Args:
            post: Normalized post data

        Returns:
            True if inserted, False if updated
        """
        source_id = self._resolve_source_id(post)

        with get_session() as session:
            existing = session.execute(
                select(Post).where(
                    Post.source_id == source_id,
                    Post.external_id == post.external_id,
                )
            ).scalar_one_or_none()

            values = post.model_dump(exclude={"source_name", "source_type"})
            values["source_id"] = source_id

            if existing:
                # Update existing record
                exclude_fields = {"source_id", "external_id", "crawl_source", "crawled_at"}
                for key, value in values.items():
                    if key in exclude_fields:
                        continue
                    setattr(existing, key, value)
                logger.debug(f"Updated post {post.platform}:{post.external_id}")
                return False
            else:
                # Insert new record
                new_post = Post(**values)
                session.add(new_post)
                logger.debug(f"Inserted post {post.platform}:{post.external_id}")
                return True

    def exists(self, post_id: int, source_id: int | None = None) -> bool:
        """Check if a post already exists in the database.

        Args:
            post_id: The post ID to check

        Returns:
            True if exists, False otherwise
        """
        source_id = source_id or self._default_dcard_source_id()
        with get_session() as session:
            result = session.execute(
                select(Post.id).where(
                    Post.source_id == source_id,
                    Post.external_id == str(post_id),
                )
            ).scalar_one_or_none()
            return result is not None

    def exists_external(self, source_id: int, external_id: str) -> bool:
        """Check if a platform item already exists by source/external ID."""
        with get_session() as session:
            result = session.execute(
                select(Post.id).where(Post.source_id == source_id, Post.external_id == external_id)
            ).scalar_one_or_none()
            return result is not None

    def get_by_id(self, post_id: int) -> Post | None:
        """Get a post by ID.

        Args:
            post_id: The post ID

        Returns:
            Post object or None
        """
        source_id = self._default_dcard_source_id()
        with get_session() as session:
            return session.execute(
                select(Post).where(Post.source_id == source_id, Post.external_id == str(post_id))
            ).scalar_one_or_none()

    def get_by_external_id(self, source_id: int, external_id: str) -> Post | None:
        """Get a post by source and external ID."""
        with get_session() as session:
            return session.execute(
                select(Post).where(Post.source_id == source_id, Post.external_id == external_id)
            ).scalar_one_or_none()

    def count(self) -> int:
        """Get total post count.

        Returns:
            Number of posts in database
        """
        with get_session() as session:
            from sqlalchemy import func
            return session.execute(select(func.count(Post.id))).scalar()

    def _resolve_source_id(self, post: NormalizedPost) -> int:
        if post.source_id is not None:
            return post.source_id
        return self.source_repository.get_or_create(
            name=post.source_name,
            source_type=post.source_type,
            base_url="https://www.dcard.tw" if post.platform == "dcard" else None,
        )

    def _default_dcard_source_id(self) -> int:
        return self.source_repository.get_or_create(
            name="dcard",
            source_type="forum",
            base_url="https://www.dcard.tw",
            robots_url="https://www.dcard.tw/robots.txt",
        )
