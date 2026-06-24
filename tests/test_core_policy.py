"""Tests for fail-closed crawler policy."""

import pytest

from dcard_crawler.core.errors import AccessForbiddenError, ChallengeDetectedError, RateLimitedError
from dcard_crawler.core.policy import CrawlPolicy


def test_policy_blocks_403():
    policy = CrawlPolicy()

    with pytest.raises(AccessForbiddenError):
        policy.raise_if_blocked(403, "Forbidden")


def test_policy_blocks_429():
    policy = CrawlPolicy()

    with pytest.raises(RateLimitedError):
        policy.raise_if_blocked(429, "Too many requests")


def test_policy_detects_challenge_pages():
    policy = CrawlPolicy()

    with pytest.raises(ChallengeDetectedError):
        policy.raise_if_blocked(200, "<html>Cloudflare verify you are human captcha</html>")


def test_policy_allows_normal_200():
    policy = CrawlPolicy()

    policy.raise_if_blocked(200, "<html><title>Public page</title></html>")
