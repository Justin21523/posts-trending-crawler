"""Fail-closed request and response policy helpers."""

from dataclasses import dataclass

from dcard_crawler.core.errors import (
    AccessForbiddenError,
    ChallengeDetectedError,
    CrawlerError,
    ErrorCategory,
    RateLimitedError,
)


@dataclass(frozen=True)
class PolicyDecision:
    """Decision returned by response classification."""

    allowed: bool
    category: ErrorCategory
    reason: str


class CrawlPolicy:
    """Classify responses and stop on blocks instead of bypassing them."""

    challenge_markers = (
        "captcha",
        "turnstile",
        "recaptcha",
        "cf-challenge",
        "cloudflare",
        "checking your browser",
        "verify you are human",
        "unusual traffic",
        "login required",
        "sign in to continue",
        "請先登入",
        "驗證您是人類",
        "稍候",
    )

    def classify(self, status_code: int, text: str = "") -> PolicyDecision:
        """Classify HTTP status and body text."""
        lowered = text.lower()
        if status_code == 429:
            return PolicyDecision(False, ErrorCategory.RATE_LIMITED, "http_429_rate_limited")
        if status_code == 403:
            return PolicyDecision(False, ErrorCategory.FORBIDDEN, "http_403_forbidden")
        if any(marker in lowered for marker in self.challenge_markers):
            return PolicyDecision(False, ErrorCategory.CHALLENGE, "challenge_or_login_detected")
        if 500 <= status_code < 600:
            return PolicyDecision(True, ErrorCategory.SERVER_ERROR, "server_error_retryable")
        if 400 <= status_code < 500:
            return PolicyDecision(
                False,
                ErrorCategory.CLIENT_ERROR,
                f"http_{status_code}_client_error",
            )
        return PolicyDecision(True, ErrorCategory.UNKNOWN, "allowed")

    def raise_if_blocked(self, status_code: int, text: str = "") -> None:
        """Raise a typed crawler error if the response should fail closed."""
        decision = self.classify(status_code=status_code, text=text)
        if decision.allowed:
            return

        message = f"Request blocked by policy: {decision.reason}"
        if decision.category == ErrorCategory.RATE_LIMITED:
            raise RateLimitedError(message, status_code=status_code)
        if decision.category == ErrorCategory.FORBIDDEN:
            raise AccessForbiddenError(message, status_code=status_code)
        if decision.category == ErrorCategory.CHALLENGE:
            raise ChallengeDetectedError(message, status_code=status_code)
        raise CrawlerError(message, status_code=status_code)
