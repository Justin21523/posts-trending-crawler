"""Repository for crawl source records."""

from sqlalchemy import select

from dcard_crawler.database import get_session
from dcard_crawler.models import Source


class SourceRepository:
    """Database repository for public data sources."""

    def get_or_create(
        self,
        name: str,
        source_type: str = "forum",
        base_url: str | None = None,
        robots_url: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Return the source ID, creating the source if necessary."""
        with get_session() as session:
            source = session.execute(
                select(Source).where(Source.name == name)
            ).scalar_one_or_none()

            if source:
                return int(source.id)

            source = Source(
                name=name,
                source_type=source_type,
                base_url=base_url,
                robots_url=robots_url,
                notes=notes,
            )
            session.add(source)
            session.flush()
            return int(source.id)

    def get_by_name(self, name: str) -> Source | None:
        """Get a source by name."""
        with get_session() as session:
            return session.execute(select(Source).where(Source.name == name)).scalar_one_or_none()
