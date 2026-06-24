"""Quality validation service for crawled posts."""


from loguru import logger

from dcard_crawler.schemas import NormalizedPost


class QualityService:
    """Service for validating post data quality."""

    def validate(self, post: NormalizedPost) -> tuple[bool, list[str]]:
        """Validate a normalized post for data quality.

        Args:
            post: The post to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check required fields
        if not post.title or not post.title.strip():
            issues.append("title is empty")

        if not post.post_id:
            issues.append("post_id is missing")

        if not post.external_id:
            issues.append("external_id is missing")

        if not post.platform:
            issues.append("platform is missing")

        # Check content quality
        if not post.content and not post.excerpt:
            issues.append("both content and excerpt are empty")

        # Check for suspicious content
        if post.content and len(post.content.strip()) < 10:
            issues.append(f"content is suspiciously short ({len(post.content.strip())} chars)")

        # Check URL consistency
        if post.url:
            if not post.url.startswith("https://www.dcard.tw/"):
                issues.append(f"invalid URL format: {post.url}")
            if post.forum_alias and post.forum_alias not in post.url:
                logger.debug(f"forum_alias '{post.forum_alias}' not found in URL: {post.url}")

        # Check timestamp
        if not post.created_at:
            issues.append("created_at is missing")

        # Check raw_json presence
        if not post.raw_json:
            issues.append("raw_json is empty (data may be incomplete)")

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning(f"Post {post.post_id} validation issues: {issues}")

        return is_valid, issues

    def validate_batch(self, posts: list[NormalizedPost]) -> dict:
        """Validate a batch of posts and return summary statistics.

        Args:
            posts: List of posts to validate

        Returns:
            Summary dict with validation results
        """
        valid_count = 0
        invalid_count = 0
        all_issues = []

        for post in posts:
            is_valid, issues = self.validate(post)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_issues.extend(issues)

        summary = {
            "total": len(posts),
            "valid": valid_count,
            "invalid": invalid_count,
            "issues": all_issues,
        }

        logger.info(f"Batch validation: {valid_count}/{len(posts)} valid, {invalid_count} invalid")
        return summary
