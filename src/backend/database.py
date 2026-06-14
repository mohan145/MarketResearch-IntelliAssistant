import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.backend.config import get_settings

settings = get_settings()


def _build_engine():
    """Create SQLAlchemy engine.

    Local:      SQLite file at ./data/market_research.db
    Production: SQLite file on Azure File Share at /app/data/market_research.db
    """
    db_url = settings.database_url

    if db_url.startswith("sqlite"):
        # Ensure the data directory exists before SQLite tries to create the file
        db_path = db_url.replace("sqlite:///", "").replace("sqlite:////", "/")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        return create_engine(db_url, connect_args={"check_same_thread": False})

    return create_engine(db_url)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables. Safe to call multiple times — skips existing tables."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()