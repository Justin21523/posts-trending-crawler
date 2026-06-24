"""Tests for text and HTML helpers."""

from dcard_crawler.core.html_utils import extract_canonical_url, extract_text
from dcard_crawler.core.text_utils import content_hash, normalize_text, normalize_whitespace


def test_text_normalization_and_hash_are_stable():
    assert normalize_whitespace("  hello\n  world  ") == "hello world"
    assert normalize_text("  Hello WORLD  ") == "hello world"
    assert content_hash("a", "b") == content_hash(" a ", "b")


def test_html_text_and_canonical_extraction():
    html = """
    <html>
      <head><link rel="canonical" href="https://example.com/post/1"></head>
      <body><script>hidden()</script><article>Hello <b>world</b></article></body>
    </html>
    """

    assert extract_text(html) == "Hello world"
    assert extract_canonical_url(html) == "https://example.com/post/1"
