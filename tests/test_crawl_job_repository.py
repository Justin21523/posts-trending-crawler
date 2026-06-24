"""Tests for crawl job lifecycle repository."""

from dcard_crawler.database import init_db
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.settings import settings


def test_crawl_job_finish_records_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    repository = CrawlJobRepository()
    job_id = repository.start(source_id, "dcard_posts", "https://www.dcard.tw/f/trending")

    repository.finish(job_id, request_count=2, item_count=1)

    job = repository.get_by_id(job_id)
    assert job is not None
    assert job.status == "completed"
    assert job.finished_at is not None
    assert job.request_count == 2
    assert job.item_count == 1


def test_crawl_job_fail_records_error_classification(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    repository = CrawlJobRepository()
    job_id = repository.start(source_id, "dcard_posts")

    repository.fail(
        job_id,
        error_message="Request blocked by policy",
        request_count=1,
        item_count=0,
        error_category="rate_limited",
        error_reason="http_429_rate_limited",
    )

    job = repository.get_by_id(job_id)
    assert job is not None
    assert job.status == "failed"
    assert job.error_category == "rate_limited"
    assert job.error_reason == "http_429_rate_limited"
