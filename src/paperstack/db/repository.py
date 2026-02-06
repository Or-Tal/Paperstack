"""Repository pattern for database operations."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from .models import (
    Annotation,
    DoneEntry,
    Embedding,
    Paper,
    PaperStatus,
    Preference,
    SearchMemory,
    Trajectory,
)
from .session import get_session


class Repository:
    """Repository for all database operations."""

    def __init__(self, session: Session | None = None):
        self._session = session

    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def commit(self) -> None:
        """Commit current transaction."""
        self.session.commit()

    def close(self) -> None:
        """Close session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    # Paper operations
    def add_paper(
        self,
        url: str,
        title: str,
        authors: str | None = None,
        abstract: str | None = None,
        doi: str | None = None,
        arxiv_id: str | None = None,
        bibtex: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        pdf_path: str | None = None,
    ) -> Paper:
        """Add a new paper."""
        paper = Paper(
            url=url,
            title=title,
            authors=authors,
            abstract=abstract,
            doi=doi,
            arxiv_id=arxiv_id,
            bibtex=bibtex,
            tags=json.dumps(tags) if tags else None,
            description=description,
            pdf_path=pdf_path,
            status=PaperStatus.READING.value,
        )
        self.session.add(paper)
        self.session.commit()
        return paper

    def get_paper(self, paper_id: int) -> Paper | None:
        """Get paper by ID."""
        return self.session.get(Paper, paper_id)

    def get_paper_by_url(self, url: str) -> Paper | None:
        """Get paper by URL."""
        stmt = select(Paper).where(Paper.url == url)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_paper_by_arxiv(self, arxiv_id: str) -> Paper | None:
        """Get paper by arXiv ID."""
        stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_paper_by_doi(self, doi: str) -> Paper | None:
        """Get paper by DOI."""
        stmt = select(Paper).where(Paper.doi == doi)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_papers(self, status: str | None = None) -> list[Paper]:
        """List papers, optionally filtered by status."""
        stmt = select(Paper).order_by(Paper.added_at.desc())
        if status:
            stmt = stmt.where(Paper.status == status)
        return list(self.session.execute(stmt).scalars().all())

    def list_reading(self) -> list[Paper]:
        """List papers in reading status."""
        return self.list_papers(status=PaperStatus.READING.value)

    def list_done(self) -> list[Paper]:
        """List completed papers."""
        return self.list_papers(status=PaperStatus.DONE.value)

    def update_paper(self, paper_id: int, **kwargs) -> Paper | None:
        """Update paper fields."""
        paper = self.get_paper(paper_id)
        if paper is None:
            return None
        for key, value in kwargs.items():
            if key == "tags" and isinstance(value, list):
                value = json.dumps(value)
            if hasattr(paper, key):
                setattr(paper, key, value)
        self.session.commit()
        return paper

    def delete_paper(self, paper_id: int) -> bool:
        """Delete a paper."""
        paper = self.get_paper(paper_id)
        if paper is None:
            return False
        self.session.delete(paper)
        self.session.commit()
        return True

    # Annotation operations
    def add_annotation(
        self,
        paper_id: int,
        page: int,
        annotation_type: str,
        content: str | None = None,
        selection_text: str | None = None,
        position: dict | None = None,
        color: str = "#ffeb3b",
    ) -> Annotation:
        """Add an annotation to a paper."""
        annotation = Annotation(
            paper_id=paper_id,
            page=page,
            type=annotation_type,
            content=content,
            selection_text=selection_text,
            position=json.dumps(position) if position else None,
            color=color,
        )
        self.session.add(annotation)
        self.session.commit()
        return annotation

    def get_annotations(self, paper_id: int) -> list[Annotation]:
        """Get all annotations for a paper."""
        stmt = (
            select(Annotation)
            .where(Annotation.paper_id == paper_id)
            .order_by(Annotation.page, Annotation.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())

    def delete_annotation(self, annotation_id: int) -> bool:
        """Delete an annotation."""
        annotation = self.session.get(Annotation, annotation_id)
        if annotation is None:
            return False
        self.session.delete(annotation)
        self.session.commit()
        return True

    # Done entry operations
    def mark_done(
        self,
        paper_id: int,
        user_concepts: list[str] | None = None,
        compressed_summary: str | None = None,
        key_contributions: str | None = None,
    ) -> DoneEntry | None:
        """Mark a paper as done with learned concepts."""
        paper = self.get_paper(paper_id)
        if paper is None:
            return None

        # Update paper status
        paper.status = PaperStatus.DONE.value

        # Create or update done entry
        if paper.done_entry is None:
            done_entry = DoneEntry(
                paper_id=paper_id,
                user_concepts=json.dumps(user_concepts) if user_concepts else None,
                compressed_summary=compressed_summary,
                key_contributions=key_contributions,
            )
            self.session.add(done_entry)
        else:
            done_entry = paper.done_entry
            if user_concepts:
                done_entry.user_concepts = json.dumps(user_concepts)
            if compressed_summary:
                done_entry.compressed_summary = compressed_summary
            if key_contributions:
                done_entry.key_contributions = key_contributions

        self.session.commit()
        return done_entry

    def get_done_entry(self, paper_id: int) -> DoneEntry | None:
        """Get done entry for a paper."""
        stmt = select(DoneEntry).where(DoneEntry.paper_id == paper_id)
        return self.session.execute(stmt).scalar_one_or_none()

    # Embedding operations
    def add_embedding(
        self,
        paper_id: int,
        content_type: str,
        embedding: bytes,
        text_content: str,
    ) -> Embedding:
        """Add an embedding for a paper."""
        emb = Embedding(
            paper_id=paper_id,
            content_type=content_type,
            embedding=embedding,
            text_content=text_content,
        )
        self.session.add(emb)
        self.session.commit()
        return emb

    def get_embeddings(self, paper_id: int | None = None) -> list[Embedding]:
        """Get embeddings, optionally filtered by paper."""
        stmt = select(Embedding)
        if paper_id is not None:
            stmt = stmt.where(Embedding.paper_id == paper_id)
        return list(self.session.execute(stmt).scalars().all())

    def delete_embeddings(self, paper_id: int) -> int:
        """Delete all embeddings for a paper."""
        stmt = delete(Embedding).where(Embedding.paper_id == paper_id)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    # Search memory operations
    def add_search_memory(
        self,
        query: str,
        query_embedding: bytes | None = None,
        results: dict | None = None,
        retention_days: int = 30,
    ) -> SearchMemory:
        """Add a search query to memory."""
        memory = SearchMemory(
            query=query,
            query_embedding=query_embedding,
            results=json.dumps(results) if results else None,
            expires_at=datetime.utcnow() + timedelta(days=retention_days),
        )
        self.session.add(memory)
        self.session.commit()
        return memory

    def update_search_feedback(
        self, memory_id: int, feedback: dict
    ) -> SearchMemory | None:
        """Update feedback for a search memory entry."""
        memory = self.session.get(SearchMemory, memory_id)
        if memory is None:
            return None
        memory.feedback = json.dumps(feedback)
        self.session.commit()
        return memory

    def cleanup_expired_memory(self) -> int:
        """Delete expired search memory entries."""
        stmt = delete(SearchMemory).where(SearchMemory.expires_at < datetime.utcnow())
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    # Trajectory operations
    def add_trajectory_step(
        self,
        session_id: str,
        step: int,
        action: str,
        query: str | None = None,
        results_summary: str | None = None,
    ) -> Trajectory:
        """Add a step to a search trajectory."""
        trajectory = Trajectory(
            session_id=session_id,
            step=step,
            action=action,
            query=query,
            results_summary=results_summary,
        )
        self.session.add(trajectory)
        self.session.commit()
        return trajectory

    def get_trajectory(self, session_id: str) -> list[Trajectory]:
        """Get all steps in a search trajectory."""
        stmt = (
            select(Trajectory)
            .where(Trajectory.session_id == session_id)
            .order_by(Trajectory.step)
        )
        return list(self.session.execute(stmt).scalars().all())

    # Preference operations
    def get_preference(self, key: str) -> str | None:
        """Get a preference value."""
        pref = self.session.get(Preference, key)
        return pref.value if pref else None

    def set_preference(self, key: str, value: str) -> Preference:
        """Set a preference value."""
        pref = self.session.get(Preference, key)
        if pref is None:
            pref = Preference(key=key, value=value)
            self.session.add(pref)
        else:
            pref.value = value
        self.session.commit()
        return pref

    def get_all_preferences(self) -> dict[str, str]:
        """Get all preferences as a dictionary."""
        stmt = select(Preference)
        prefs = self.session.execute(stmt).scalars().all()
        return {p.key: p.value for p in prefs}

    def delete_preference(self, key: str) -> bool:
        """Delete a preference."""
        pref = self.session.get(Preference, key)
        if pref is None:
            return False
        self.session.delete(pref)
        self.session.commit()
        return True
