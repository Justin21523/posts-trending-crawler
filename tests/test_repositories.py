"""Tests for source and post repositories."""

from dcard_crawler.database import init_db
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.settings import settings


def test_dcard_post_upsert_deduplicates_by_source_external_id(tmp_path, monkeypatch):
    """The same Dcard external ID should update rather than duplicate."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    repository = PostRepository()
    post = NormalizedPost(
        source_id=source_id,
        platform="dcard",
        external_id="12345",
        post_id=12345,
        title="Original title",
        content="Long enough content for validation",
        created_at="2024-01-01T12:00:00Z",
        raw_json={"id": 12345},
    )

    assert repository.upsert(post) is True
    post.title = "Updated title"
    assert repository.upsert(post) is False

    stored = repository.get_by_external_id(source_id, "12345")
    assert repository.count() == 1
    assert stored is not None
    assert stored.title == "Updated title"


def test_same_external_id_can_exist_for_different_sources(tmp_path, monkeypatch):
    """Different sources may use the same external ID without colliding."""
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)

    sources = SourceRepository()
    dcard_source_id = sources.get_or_create("dcard", source_type="forum")
    ptt_source_id = sources.get_or_create("ptt", source_type="forum")
    repository = PostRepository()

    for source_id, platform in [(dcard_source_id, "dcard"), (ptt_source_id, "ptt")]:
        repository.upsert(
            NormalizedPost(
                source_id=source_id,
                source_name=platform,
                platform=platform,
                external_id="same-id",
                post_id=1,
                title=f"{platform} title",
                content="Long enough content for validation",
                created_at="2024-01-01T12:00:00Z",
                raw_json={"id": "same-id"},
            )
        )

    assert repository.count() == 2
