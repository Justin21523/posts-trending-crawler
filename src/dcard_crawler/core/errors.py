"""Crawler error types and classifications."""

from enum import Enum


class ErrorCategory(str, Enum):
    """High-level crawler error category."""

    TRANSIENT = "transient"
    RATE_LIMITED = "rate_limited"
    FORBIDDEN = "forbidden"
    CHALLENGE = "challenge"
    ROBOTS_DISALLOWED = "robots_disallowed"
    BUDGET_EXCEEDED = "budget_exceeded"
    CLIENT_ERROR = "client_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class CrawlerError(Exception):
    """Base exception raised by crawler core."""

    category: ErrorCategory = ErrorCategory.UNKNOWN

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PolicyBlockedError(CrawlerError):
    """Raised when policy says a request should fail closed."""

    category = ErrorCategory.CHALLENGE


class RateLimitedError(PolicyBlockedError):
    """Raised for HTTP 429 or rate-limit pages."""

    category = ErrorCategory.RATE_LIMITED


class AccessForbiddenError(PolicyBlockedError):
    """Raised for HTTP 403 or access denied pages."""

    category = ErrorCategory.FORBIDDEN


class ChallengeDetectedError(PolicyBlockedError):
    """Raised for CAPTCHA, challenge, or login wall pages."""

    category = ErrorCategory.CHALLENGE


class RobotsDisallowedError(PolicyBlockedError):
    """Raised when robots.txt disallows a URL."""

    category = ErrorCategory.ROBOTS_DISALLOWED


class RequestBudgetExceededError(PolicyBlockedError):
    """Raised when a domain or client request budget is exhausted."""

    category = ErrorCategory.BUDGET_EXCEEDED
