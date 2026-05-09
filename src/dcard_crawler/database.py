"""Database setup and session management."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from dcard_crawler.settings import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_engine():
    """Create SQLAlchemy engine with proper settings."""
    db_url = settings.database.url

    # Ensure data directory exists for SQLite
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
    )
    return engine


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session():
    """Get a database session context manager."""
    engine = get_engine()
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
