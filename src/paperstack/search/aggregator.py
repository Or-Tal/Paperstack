"""Search aggregator for external sources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from paperstack.config import get_settings
from paperstack.core.schemas import ExternalPaper, SearchResultPage
from paperstack.metadata import ArxivClient, CrossRefClient, SemanticScholarClient


@dataclass
class SearchState:
    """State for paginated search."""

    query: str
    results: list[ExternalPaper]
    current_page: int
    per_page: int
    total_fetched: int
    max_results: int
    sources_exhausted: set[str]


class SearchAggregator:
    """Aggregates search results from multiple sources."""

    def __init__(self):
        self.arxiv = ArxivClient()
        self.semantic_scholar = SemanticScholarClient()
        self.crossref = CrossRefClient()
        settings = get_settings()
        self.per_page = settings.search_results_per_page
        self.max_results = settings.max_search_results

    def search(
        self,
        query: str,
        max_results: int | None = None,
        sources: list[str] | None = None,
    ) -> list[ExternalPaper]:
        """Search all sources and return aggregated results."""
        if max_results is None:
            max_results = self.max_results

        if sources is None:
            sources = ["semantic_scholar", "arxiv", "crossref"]

        results: list[ExternalPaper] = []
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()
        seen_titles: set[str] = set()

        def add_result(paper: ExternalPaper) -> bool:
            """Add paper if not duplicate. Returns True if added."""
            # Check for duplicates
            if paper.doi and paper.doi in seen_dois:
                return False
            if paper.arxiv_id and paper.arxiv_id in seen_arxiv_ids:
                return False
            title_key = paper.title.lower().strip()
            if title_key in seen_titles:
                return False

            # Add to seen sets
            if paper.doi:
                seen_dois.add(paper.doi)
            if paper.arxiv_id:
                seen_arxiv_ids.add(paper.arxiv_id)
            seen_titles.add(title_key)

            results.append(paper)
            return True

        # Search each source
        per_source = max_results // len(sources) + 1

        if "semantic_scholar" in sources:
            for paper in self._search_semantic_scholar(query, per_source):
                add_result(paper)

        if "arxiv" in sources:
            for paper in self._search_arxiv(query, per_source):
                add_result(paper)

        if "crossref" in sources:
            for paper in self._search_crossref(query, per_source):
                add_result(paper)

        # Sort by citation count (if available) and limit
        results.sort(key=lambda p: p.citation_count or 0, reverse=True)
        return results[:max_results]

    def _search_semantic_scholar(self, query: str, limit: int) -> Iterator[ExternalPaper]:
        """Search Semantic Scholar."""
        papers = self.semantic_scholar.search(query, limit=limit)
        for paper in papers:
            yield ExternalPaper(
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                url=paper.url,
                doi=paper.doi,
                arxiv_id=paper.arxiv_id,
                year=paper.year,
                venue=paper.venue,
                citation_count=paper.citation_count,
                source="semantic_scholar",
            )

    def _search_arxiv(self, query: str, limit: int) -> Iterator[ExternalPaper]:
        """Search arXiv."""
        papers = self.arxiv.search(query, max_results=limit)
        for paper in papers:
            year = int(paper.published[:4]) if paper.published else None
            yield ExternalPaper(
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                url=f"https://arxiv.org/abs/{paper.arxiv_id}",
                doi=paper.doi,
                arxiv_id=paper.arxiv_id,
                year=year,
                venue="arXiv",
                citation_count=None,
                source="arxiv",
            )

    def _search_crossref(self, query: str, limit: int) -> Iterator[ExternalPaper]:
        """Search CrossRef."""
        papers = self.crossref.search(query, rows=limit)
        for paper in papers:
            year = int(paper.published[:4]) if paper.published else None
            yield ExternalPaper(
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                url=paper.url,
                doi=paper.doi,
                arxiv_id=None,
                year=year,
                venue=paper.venue,
                citation_count=paper.is_referenced_by_count,
                source="crossref",
            )

    def search_paginated(self, query: str) -> SearchState:
        """Start a paginated search. Returns initial state."""
        results = self.search(query)
        return SearchState(
            query=query,
            results=results,
            current_page=1,
            per_page=self.per_page,
            total_fetched=len(results),
            max_results=self.max_results,
            sources_exhausted=set(),
        )

    def get_page(self, state: SearchState, page: int) -> SearchResultPage:
        """Get a specific page from search state."""
        start = (page - 1) * state.per_page
        end = start + state.per_page
        page_results = state.results[start:end]

        total_pages = (len(state.results) + state.per_page - 1) // state.per_page

        return SearchResultPage(
            results=page_results,
            total=len(state.results),
            page=page,
            per_page=state.per_page,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    def get_bibtex(self, paper: ExternalPaper) -> str | None:
        """Get BibTeX for an external paper."""
        if paper.source == "arxiv" and paper.arxiv_id:
            arxiv_paper = self.arxiv.get_paper(paper.arxiv_id)
            if arxiv_paper:
                return self.arxiv.generate_bibtex(arxiv_paper)

        if paper.source == "semantic_scholar":
            if paper.arxiv_id:
                ss_paper = self.semantic_scholar.get_paper_by_arxiv(paper.arxiv_id)
            elif paper.doi:
                ss_paper = self.semantic_scholar.get_paper_by_doi(paper.doi)
            else:
                ss_paper = None
            if ss_paper:
                return self.semantic_scholar.generate_bibtex(ss_paper)

        if paper.doi:
            cr_paper = self.crossref.get_paper_by_doi(paper.doi)
            if cr_paper:
                return self.crossref.generate_bibtex(cr_paper)

        return None
