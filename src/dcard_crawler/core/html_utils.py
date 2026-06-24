"""HTML parsing helpers."""

from bs4 import BeautifulSoup


def extract_text(html: str) -> str:
    """Extract visible text from HTML."""
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())


def extract_canonical_url(html: str) -> str | None:
    """Extract canonical URL from HTML if present."""
    soup = BeautifulSoup(html or "", "lxml")
    tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    if not tag:
        return None
    href = tag.get("href")
    return str(href) if href else None
