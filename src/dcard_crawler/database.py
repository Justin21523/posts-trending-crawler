"""Database setup and session management."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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


def init_db(reset: bool = False):
    """Initialize database tables."""
    engine = get_engine()
    if reset:
        drop_all_tables()
    Base.metadata.create_all(engine)
    return engine


def has_table(table_name: str) -> bool:
    """Check whether a database table exists."""
    engine = get_engine()
    return inspect(engine).has_table(table_name)


def get_table_columns(table_name: str) -> set[str]:
    """Return column names for an existing table."""
    engine = get_engine()
    if not inspect(engine).has_table(table_name):
        return set()
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def is_current_schema() -> bool:
    """Check whether the SQLite schema matches the Phase 1A model."""
    required_tables = {"sources", "crawl_jobs", "posts", "post_metrics"}
    engine = get_engine()
    inspector = inspect(engine)
    if not required_tables.issubset(set(inspector.get_table_names())):
        return False

    post_columns = get_table_columns("posts")
    crawl_job_columns = get_table_columns("crawl_jobs")
    return {"source_id", "external_id", "platform"}.issubset(post_columns) and {
        "error_category",
        "error_reason",
    }.issubset(crawl_job_columns)


def drop_all_tables():
    """Drop all tables, including legacy tables unknown to current metadata."""
    engine = get_engine()
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name in inspector.get_table_names():
            connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))


@contextmanager
def get_session():
    """Get a database session context manager."""
    engine = get_engine()
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
