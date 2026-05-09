"""Structured logging configuration."""

import sys
from pathlib import Path

from loguru import logger

from dcard_crawler.settings import settings


def setup_logging():
    """Configure loguru logger."""
    # Remove default handler
    logger.remove()

    # Ensure log directory exists
    log_file = Path(settings.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Console handler
    console_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
        "<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=settings.logging.level,
        format=console_fmt,
        colorize=True,
    )

    # File handler
    logger.add(
        log_file,
        level=settings.logging.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
    )

    return logger


# Initialize logger on import
setup_logging()

__all__ = ["logger"]
