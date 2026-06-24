"""Text normalization and hashing helpers."""

import hashlib
import re


def normalize_whitespace(text: str | None) -> str:
    """Normalize whitespace in user-visible text."""
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_text(text: str | None) -> str:
    """Normalize text for lightweight matching and analysis."""
    return normalize_whitespace(text).lower()


def content_hash(*parts: str | None) -> str:
    """Create a deterministic SHA-256 content hash."""
    text = "\n".join(normalize_whitespace(part) for part in parts if part)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
