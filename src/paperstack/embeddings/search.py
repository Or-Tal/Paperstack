"""Semantic search over paper embeddings."""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from paperstack.core.schemas import PaperResponse, SearchResult
from paperstack.db import Repository
from paperstack.db.models import ContentType

from .encoder import EmbeddingEncoder, get_encoder


@dataclass
class SearchMatch:
    """A search match with score."""

    paper_id: int
    score: float
    content_type: str
    matched_text: str


class SemanticSearch:
    """Semantic search over paper embeddings."""

    def __init__(
        self,
        repo: Repository | None = None,
        encoder: EmbeddingEncoder | None = None,
    ):
        self.repo = repo or Repository()
        self.encoder = encoder or get_encoder()

    def index_paper(self, paper_id: int) -> int:
        """Create embeddings for a paper. Returns number of embeddings created."""
        paper = self.repo.get_paper(paper_id)
        if paper is None:
            return 0

        # Delete existing embeddings
        self.repo.delete_embeddings(paper_id)

        count = 0

        # Embed abstract
        if paper.abstract:
            embedding = self.encoder.encode(paper.abstract)
            self.repo.add_embedding(
                paper_id=paper_id,
                content_type=ContentType.ABSTRACT.value,
                embedding=self.encoder.to_bytes(embedding),
                text_content=paper.abstract,
            )
            count += 1

        # Embed done entry summary if exists
        done_entry = self.repo.get_done_entry(paper_id)
        if done_entry:
            if done_entry.compressed_summary:
                embedding = self.encoder.encode(done_entry.compressed_summary)
                self.repo.add_embedding(
                    paper_id=paper_id,
                    content_type=ContentType.SUMMARY.value,
                    embedding=self.encoder.to_bytes(embedding),
                    text_content=done_entry.compressed_summary,
                )
                count += 1

            if done_entry.user_concepts:
                concepts = json.loads(done_entry.user_concepts)
                if concepts:
                    concepts_text = ", ".join(concepts)
                    embedding = self.encoder.encode(concepts_text)
                    self.repo.add_embedding(
                        paper_id=paper_id,
                        content_type=ContentType.CONCEPTS.value,
                        embedding=self.encoder.to_bytes(embedding),
                        text_content=concepts_text,
                    )
                    count += 1

        return count

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        done_only: bool = True,
    ) -> list[SearchResult]:
        """Search for papers matching the query."""
        # Encode query
        query_embedding = self.encoder.encode(query)

        # Get all embeddings
        all_embeddings = self.repo.get_embeddings()

        if not all_embeddings:
            return []

        # Filter by done papers if requested
        if done_only:
            done_papers = {p.id for p in self.repo.list_done()}
            all_embeddings = [e for e in all_embeddings if e.paper_id in done_papers]

        if not all_embeddings:
            return []

        # Convert to numpy arrays
        paper_ids = [e.paper_id for e in all_embeddings]
        content_types = [e.content_type for e in all_embeddings]
        text_contents = [e.text_content for e in all_embeddings]
        embeddings = np.array([self.encoder.from_bytes(e.embedding) for e in all_embeddings])

        # Compute similarities
        similarities = self.encoder.cosine_similarity_batch(query_embedding, embeddings)

        # Get top matches
        matches: dict[int, SearchMatch] = {}
        for idx in np.argsort(similarities)[::-1]:
            score = float(similarities[idx])
            if score < min_score:
                break

            paper_id = paper_ids[idx]
            # Keep best match per paper
            if paper_id not in matches or score > matches[paper_id].score:
                matches[paper_id] = SearchMatch(
                    paper_id=paper_id,
                    score=score,
                    content_type=content_types[idx],
                    matched_text=text_contents[idx][:300],
                )

            if len(matches) >= top_k:
                break

        # Build results
        results = []
        for match in sorted(matches.values(), key=lambda m: m.score, reverse=True):
            paper = self.repo.get_paper(match.paper_id)
            if paper:
                done_entry = self.repo.get_done_entry(match.paper_id)
                summary = done_entry.compressed_summary if done_entry else None

                results.append(
                    SearchResult(
                        paper=PaperResponse.model_validate(paper),
                        score=match.score,
                        summary=summary,
                        matched_content=match.matched_text,
                    )
                )

        return results

    def find_similar(self, paper_id: int, top_k: int = 5) -> list[SearchResult]:
        """Find papers similar to a given paper."""
        paper = self.repo.get_paper(paper_id)
        if paper is None or not paper.abstract:
            return []

        # Use abstract as query
        return self.search(paper.abstract, top_k=top_k + 1, done_only=False)[1:]

    def reindex_all(self) -> int:
        """Reindex all papers. Returns total embeddings created."""
        total = 0
        for paper in self.repo.list_papers():
            total += self.index_paper(paper.id)
        return total
