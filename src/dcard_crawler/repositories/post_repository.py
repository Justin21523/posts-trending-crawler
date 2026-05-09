"""Repository for post persistence operations."""


from loguru import logger
from sqlalchemy import select

from dcard_crawler.database import get_session
from dcard_crawler.models import Post
from dcard_crawler.schemas import NormalizedPost


class PostRepository:
    """Database repository for post CRUD operations."""

    def upsert(self, post: NormalizedPost) -> bool:
        """Insert or update a post record.

        Args:
            post: Normalized post data

        Returns:
            True if inserted, False if updated
        """
        with get_session() as session:
            existing = session.execute(
                select(Post).where(Post.post_id == post.post_id)
            ).scalar_one_or_none()

            if existing:
                # Update existing record
                exclude_fields = {"post_id", "crawl_source", "crawled_at"}
                for key, value in post.model_dump(exclude=exclude_fields).items():
                    setattr(existing, key, value)
                logger.debug(f"Updated post {post.post_id}")
                return False
            else:
                # Insert new record
                new_post = Post(**post.model_dump())
                session.add(new_post)
                logger.debug(f"Inserted post {post.post_id}")
                return True

    def exists(self, post_id: int) -> bool:
        """Check if a post already exists in the database.

        Args:
            post_id: The post ID to check

        Returns:
            True if exists, False otherwise
        """
        with get_session() as session:
            result = session.execute(
                select(Post.post_id).where(Post.post_id == post_id)
            ).scalar_one_or_none()
            return result is not None

    def get_by_id(self, post_id: int) -> Post | None:
        """Get a post by ID.

        Args:
            post_id: The post ID

        Returns:
            Post object or None
        """
        with get_session() as session:
            return session.execute(
                select(Post).where(Post.post_id == post_id)
            ).scalar_one_or_none()

    def count(self) -> int:
        """Get total post count.

        Returns:
            Number of posts in database
        """
        with get_session() as session:
            from sqlalchemy import func
            return session.execute(select(func.count(Post.id))).scalar()
