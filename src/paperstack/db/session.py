"""Database session management."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from paperstack.config import get_settings

from .models import Base


@lru_cache
def get_engine() -> Engine:
    """Get SQLAlchemy engine."""
    settings = get_settings()
    settings.ensure_directories()
    db_url = f"sqlite:///{settings.db_path}"
    return create_engine(db_url, echo=False)


def get_session() -> Session:
    """Get a new database session."""
    engine = get_engine()
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def init_db() -> None:
    """Initialize the database, creating all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def reset_db() -> None:
    """Drop and recreate all tables. Use with caution!"""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
