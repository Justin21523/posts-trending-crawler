"""Tests for quality service."""


from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.services.quality_service import QualityService


class TestQualityService:
    """Test suite for QualityService."""

    def setup_method(self):
        self.service = QualityService()

    def test_valid_post(self):
        """Test validating a well-formed post."""
        post = NormalizedPost(
            post_id=12345,
            title="Test Post",
            content="This is a valid post with sufficient content length for validation",
            created_at="2024-01-01T12:00:00Z",
            url="https://www.dcard.tw/f/trending/p/12345",
            forum_alias="trending",
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        assert is_valid is True
        assert len(issues) == 0

    def test_empty_title_fails(self):
        """Test that empty title fails validation."""
        post = NormalizedPost(
            post_id=12345,
            title="",
            content="Some content",
            created_at="2024-01-01T12:00:00Z",
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        assert is_valid is False
        assert "title is empty" in issues

    def test_missing_post_id_fails(self):
        """Test that missing post_id fails validation."""
        post = NormalizedPost(
            post_id=0,
            title="Test",
            content="Content",
            created_at="2024-01-01T12:00:00Z",
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        assert is_valid is False
        assert "post_id is missing" in issues

    def test_empty_content_and_excerpt_fails(self):
        """Test that empty content and excerpt fails validation."""
        post = NormalizedPost(
            post_id=12345,
            title="Test",
            content="",
            excerpt="",
            created_at="2024-01-01T12:00:00Z",
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        assert is_valid is False
        assert "both content and excerpt are empty" in issues

    def test_short_content_warning(self):
        """Test that short content triggers warning."""
        post = NormalizedPost(
            post_id=12345,
            title="Test",
            content="Short",
            created_at="2024-01-01T12:00:00Z",
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        # Short content should trigger warning but may still be valid
        assert any("suspiciously short" in issue for issue in issues)

    def test_missing_created_at_fails(self):
        """Test that missing created_at fails validation."""
        post = NormalizedPost(
            post_id=12345,
            title="Test",
            content="Valid content here",
            created_at=None,
            raw_json={"id": 12345},
        )

        is_valid, issues = self.service.validate(post)

        assert is_valid is False
        assert "created_at is missing" in issues

    def test_validate_batch(self):
        """Test batch validation."""
        posts = [
            NormalizedPost(
                post_id=i,
                title=f"Post {i}",
                content=f"Content for post {i} with sufficient length",
                created_at="2024-01-01T12:00:00Z",
                raw_json={"id": i},
            )
            for i in range(1, 6)
        ]
        # Add one invalid post
        posts.append(
            NormalizedPost(
                post_id=0,
                title="",
                content="",
                excerpt="",
                created_at=None,
                raw_json={},
            )
        )

        summary = self.service.validate_batch(posts)

        assert summary["total"] == 6
        assert summary["valid"] == 5
        assert summary["invalid"] == 1
        assert len(summary["issues"]) > 0
