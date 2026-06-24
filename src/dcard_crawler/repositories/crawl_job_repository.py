"""Repository for crawl job provenance records."""

from datetime import datetime

from sqlalchemy import select

from dcard_crawler.database import get_session
from dcard_crawler.models import CrawlJob


class CrawlJobRepository:
    """Database repository for crawl job lifecycle updates."""

    def start(
        self,
        source_id: int,
        job_type: str,
        target_url: str | None = None,
    ) -> int:
        """Create a running crawl job and return its ID."""
        with get_session() as session:
            job = CrawlJob(source_id=source_id, job_type=job_type, target_url=target_url)
            session.add(job)
            session.flush()
            return int(job.id)

    def finish(self, job_id: int, request_count: int = 0, item_count: int = 0) -> None:
        """Mark a crawl job as completed."""
        self._complete(
            job_id=job_id,
            status="completed",
            request_count=request_count,
            item_count=item_count,
        )

    def fail(
        self,
        job_id: int,
        error_message: str,
        request_count: int = 0,
        item_count: int = 0,
        error_category: str | None = None,
        error_reason: str | None = None,
    ) -> None:
        """Mark a crawl job as failed."""
        self._complete(
            job_id=job_id,
            status="failed",
            error_message=error_message,
            request_count=request_count,
            item_count=item_count,
            error_category=error_category,
            error_reason=error_reason,
        )

    def warn(
        self,
        job_id: int,
        warning_message: str,
        request_count: int = 0,
        item_count: int = 0,
        error_category: str = "data_quality_warning",
        error_reason: str | None = None,
    ) -> None:
        """Mark a crawl job as completed with warnings."""
        self._complete(
            job_id=job_id,
            status="completed_with_warnings",
            error_message=warning_message,
            request_count=request_count,
            item_count=item_count,
            error_category=error_category,
            error_reason=error_reason or warning_message,
        )

    def get_by_id(self, job_id: int) -> CrawlJob | None:
        """Return a crawl job by ID."""
        with get_session() as session:
            return session.execute(
                select(CrawlJob).where(CrawlJob.id == job_id)
            ).scalar_one_or_none()

    def _complete(
        self,
        job_id: int,
        status: str,
        request_count: int = 0,
        item_count: int = 0,
        error_message: str | None = None,
        error_category: str | None = None,
        error_reason: str | None = None,
    ) -> None:
        with get_session() as session:
            job = session.execute(select(CrawlJob).where(CrawlJob.id == job_id)).scalar_one()
            job.status = status
            job.finished_at = datetime.now()
            job.request_count = request_count
            job.item_count = item_count
            job.error_message = error_message
            job.error_category = error_category
            job.error_reason = error_reason
