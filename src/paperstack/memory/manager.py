"""Memory manager for search trajectories."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from paperstack.config import get_settings
from paperstack.db import Repository
from paperstack.embeddings import EmbeddingEncoder, get_encoder


class MemoryManager:
    """Manager for search memory and trajectories."""

    def __init__(
        self,
        repo: Repository | None = None,
        encoder: EmbeddingEncoder | None = None,
    ):
        self.repo = repo or Repository()
        self._encoder = encoder  # Lazy-loaded
        settings = get_settings()
        self.retention_days = settings.memory_retention_days

    @property
    def encoder(self) -> EmbeddingEncoder:
        """Lazy-load the encoder only when needed."""
        if self._encoder is None:
            self._encoder = get_encoder()
        return self._encoder

    def start_session(self) -> str:
        """Start a new search session. Returns session ID."""
        return str(uuid.uuid4())

    def record_step(
        self,
        session_id: str,
        action: str,
        query: str | None = None,
        results_summary: str | None = None,
    ) -> None:
        """Record a step in the search trajectory."""
        # Get current step count
        trajectory = self.repo.get_trajectory(session_id)
        step = len(trajectory) + 1

        self.repo.add_trajectory_step(
            session_id=session_id,
            step=step,
            action=action,
            query=query,
            results_summary=results_summary,
        )

    def record_search(
        self,
        query: str,
        results: list[dict] | None = None,
    ) -> int:
        """Record a search query. Returns memory ID."""
        query_embedding = self.encoder.encode(query)

        memory = self.repo.add_search_memory(
            query=query,
            query_embedding=self.encoder.to_bytes(query_embedding),
            results=results,
            retention_days=self.retention_days,
        )
        return memory.id

    def record_feedback(
        self,
        memory_id: int,
        feedback: dict,
    ) -> None:
        """Record feedback on search results."""
        self.repo.update_search_feedback(memory_id, feedback)

    def get_trajectory(self, session_id: str) -> list[dict]:
        """Get full trajectory for a session."""
        steps = self.repo.get_trajectory(session_id)
        return [
            {
                "step": s.step,
                "action": s.action,
                "query": s.query,
                "results_summary": s.results_summary,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in steps
        ]

    def find_similar_searches(self, query: str, top_k: int = 5) -> list[dict]:
        """Find similar past searches."""
        query_embedding = self.encoder.encode(query)

        # This would be more efficient with proper vector indexing
        # For now, we iterate through recent searches
        # In production, consider using FAISS or similar
        from sqlalchemy import select

        from paperstack.db.models import SearchMemory
        from paperstack.db.session import get_session

        session = get_session()
        stmt = select(SearchMemory).where(
            SearchMemory.expires_at > datetime.utcnow()
        ).order_by(SearchMemory.timestamp.desc()).limit(100)

        memories = session.execute(stmt).scalars().all()

        if not memories:
            return []

        # Calculate similarities
        results = []
        for memory in memories:
            if memory.query_embedding:
                mem_embedding = self.encoder.from_bytes(memory.query_embedding)
                similarity = self.encoder.cosine_similarity(query_embedding, mem_embedding)
                results.append({
                    "query": memory.query,
                    "similarity": similarity,
                    "timestamp": memory.timestamp.isoformat(),
                    "feedback": json.loads(memory.feedback) if memory.feedback else None,
                })

        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def cleanup(self) -> int:
        """Clean up expired memory entries. Returns count deleted."""
        return self.repo.cleanup_expired_memory()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        from sqlalchemy import func, select

        from paperstack.db.models import SearchMemory, Trajectory
        from paperstack.db.session import get_session

        session = get_session()

        # Count active memories
        memory_count = session.execute(
            select(func.count(SearchMemory.id)).where(
                SearchMemory.expires_at > datetime.utcnow()
            )
        ).scalar()

        # Count trajectories
        trajectory_count = session.execute(
            select(func.count(func.distinct(Trajectory.session_id)))
        ).scalar()

        # Count total steps
        step_count = session.execute(
            select(func.count(Trajectory.id))
        ).scalar()

        return {
            "active_memories": memory_count or 0,
            "sessions": trajectory_count or 0,
            "total_steps": step_count or 0,
        }
