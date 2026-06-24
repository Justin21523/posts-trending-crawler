"""Tests for post parser."""


from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.schemas import NormalizedPost, PostDetail, PostListItem


class TestPostParser:
    """Test suite for PostParser."""

    def setup_method(self):
        self.parser = PostParser()

    def test_normalize_list_item(self):
        """Test normalizing a post from listing endpoint."""
        item = PostListItem(
            id=12345,
            title="Test Post Title",
            excerpt="Test excerpt content",
            created_at="2024-01-01T12:00:00Z",
            comment_count=10,
            like_count=50,
            topics=[{"name": "news", "id": 1}],
        )

        result = self.parser.normalize_list_item(item, "trending")

        assert isinstance(result, NormalizedPost)
        assert result.post_id == 12345
        assert result.platform == "dcard"
        assert result.external_id == "12345"
        assert result.board_or_forum == "trending"
        assert result.forum_alias == "trending"
        assert result.title == "Test Post Title"
        assert result.excerpt == "Test excerpt content"
        assert result.content == ""  # Not available in listing
        assert result.url == "https://www.dcard.tw/f/trending/p/12345"
        assert result.topics == [{"name": "news", "id": 1}]
        assert result.crawl_source == "api"
        assert result.content_hash is not None

    def test_normalize_detail(self):
        """Test normalizing a post from detail endpoint."""
        detail = PostDetail(
            id=12345,
            title="Test Post Title",
            excerpt="Excerpt",
            content="Full post content here",
            created_at="2024-01-01T12:00:00Z",
            comment_count=10,
            like_count=50,
            forum_alias="trending",
            forum_name="時事板",
            topics=[{"name": "news", "id": 1}],
            media=[
                {
                    "type": "image",
                    "url": "https://example.com/image.jpg",
                    "width": 800,
                    "height": 600,
                }
            ],
        )

        result = self.parser.normalize_detail(detail)

        assert isinstance(result, NormalizedPost)
        assert result.post_id == 12345
        assert result.external_id == "12345"
        assert result.platform == "dcard"
        assert result.content == "Full post content here"
        assert result.forum_alias == "trending"
        assert result.forum_name == "時事板"
        assert len(result.media_meta) == 1
        assert result.media_meta[0]["type"] == "image"
        assert result.media_meta[0]["url"] == "https://example.com/image.jpg"

    def test_merge_list_with_detail(self):
        """Test merging listing and detail data."""
        list_item = PostListItem(
            id=12345,
            title="Test Title",
            created_at="2024-01-01T12:00:00Z",
        )
        detail = PostDetail(
            id=12345,
            title="Test Title",
            content="Full content",
            created_at="2024-01-01T12:00:00Z",
            forum_alias="trending",
        )

        result = self.parser.merge_list_with_detail(list_item, detail, "trending")

        assert isinstance(result, NormalizedPost)
        assert result.post_id == 12345
        assert result.content == "Full content"
        assert result.forum_alias == "trending"
