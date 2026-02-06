"""SQLAlchemy models for Paperstack."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class PaperStatus(str, Enum):
    """Status of a paper."""

    READING = "reading"
    DONE = "done"
    ARCHIVED = "archived"


class AnnotationType(str, Enum):
    """Type of annotation."""

    HIGHLIGHT = "highlight"
    COMMENT = "comment"
    NOTE = "note"


class ContentType(str, Enum):
    """Type of content for embeddings."""

    ABSTRACT = "abstract"
    SUMMARY = "summary"
    CONCEPTS = "concepts"
    FULL_TEXT = "full_text"


class Paper(Base):
    """Academic paper model."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    bibtex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as string
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=PaperStatus.READING.value, nullable=False
    )
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="paper", cascade="all, delete-orphan"
    )
    done_entry: Mapped[Optional["DoneEntry"]] = relationship(
        "DoneEntry", back_populates="paper", uselist=False, cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title='{self.title[:50]}...')>"


class Annotation(Base):
    """Annotation on a paper."""

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selection_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    color: Mapped[str] = mapped_column(String(32), default="#ffeb3b", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="annotations")

    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, type='{self.type}', page={self.page})>"


class DoneEntry(Base):
    """Entry for a completed paper with learned concepts."""

    __tablename__ = "done_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_concepts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    compressed_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_contributions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="done_entry")

    def __repr__(self) -> str:
        return f"<DoneEntry(id={self.id}, paper_id={self.paper_id})>"


class Embedding(Base):
    """Embedding vector for semantic search."""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, paper_id={self.paper_id}, type='{self.content_type}')>"


class SearchMemory(Base):
    """Search query and results memory for optimization."""

    __tablename__ = "search_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<SearchMemory(id={self.id}, query='{self.query[:30]}...')>"


class Trajectory(Base):
    """Search session trajectory for agentic search."""

    __tablename__ = "trajectories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    results_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Trajectory(session={self.session_id}, step={self.step})>"


class Preference(Base):
    """User preferences storage."""

    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Preference(key='{self.key}')>"
