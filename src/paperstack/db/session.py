"""Database session management."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
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

    # Migrate: add position column if it doesn't exist
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(papers)"))
        columns = [row[1] for row in result.fetchall()]
        if "position" not in columns:
            conn.execute(
                text("ALTER TABLE papers ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
            )
            conn.commit()

        # Backfill: assign positions to existing papers that still have position=0
        rows = conn.execute(
            text(
                "SELECT id FROM papers WHERE position = 0 ORDER BY added_at ASC"
            )
        ).fetchall()
        if rows:
            for i, row in enumerate(rows, start=1):
                conn.execute(
                    text("UPDATE papers SET position = :pos WHERE id = :pid"),
                    {"pos": i, "pid": row[0]},
                )
            conn.commit()


def reset_db() -> None:
    """Drop and recreate all tables. Use with caution!"""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
