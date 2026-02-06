"""Unified metadata extractor."""
from __future__ import annotations

from dataclasses import dataclass

from .arxiv_client import ArxivClient
from .crossref_client import CrossRefClient
from .semantic_scholar import SemanticScholarClient


@dataclass
class ExtractedMetadata:
    """Extracted metadata from any source."""

    url: str
    title: str
    authors: str
    abstract: str | None
    doi: str | None
    arxiv_id: str | None
    bibtex: str
    year: int | None
    venue: str | None
    pdf_url: str | None
    source: str


class MetadataExtractor:
    """Unified metadata extractor from multiple sources."""

    def __init__(self):
        self.arxiv = ArxivClient()
        self.semantic_scholar = SemanticScholarClient()
        self.crossref = CrossRefClient()

    def extract_from_url(self, url: str) -> ExtractedMetadata | None:
        """Extract metadata from a URL."""
        # Try arXiv first
        if ArxivClient.is_arxiv_url(url):
            return self._from_arxiv(url)

        # Try Semantic Scholar for DOI or S2 URLs
        doi = SemanticScholarClient.extract_doi(url)
        if doi or "semanticscholar.org" in url:
            return self._from_semantic_scholar(url, doi)

        # Try CrossRef for DOI URLs
        if doi or "doi.org" in url:
            return self._from_crossref(url)

        # Try all sources
        return self._try_all_sources(url)

    def _from_arxiv(self, url: str) -> ExtractedMetadata | None:
        """Extract from arXiv."""
        paper = self.arxiv.get_paper_from_url(url)
        if paper is None:
            return None

        return ExtractedMetadata(
            url=url,
            title=paper.title,
            authors=", ".join(paper.authors),
            abstract=paper.abstract,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            bibtex=self.arxiv.generate_bibtex(paper),
            year=int(paper.published[:4]) if paper.published else None,
            venue="arXiv",
            pdf_url=paper.pdf_url,
            source="arxiv",
        )

    def _from_semantic_scholar(
        self, url: str, doi: str | None = None
    ) -> ExtractedMetadata | None:
        """Extract from Semantic Scholar."""
        if doi:
            paper = self.semantic_scholar.get_paper_by_doi(doi)
        else:
            paper = self.semantic_scholar.get_paper_from_url(url)

        if paper is None:
            return None

        return ExtractedMetadata(
            url=url,
            title=paper.title,
            authors=", ".join(paper.authors),
            abstract=paper.abstract,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            bibtex=self.semantic_scholar.generate_bibtex(paper),
            year=paper.year,
            venue=paper.venue,
            pdf_url=None,
            source="semantic_scholar",
        )

    def _from_crossref(self, url: str) -> ExtractedMetadata | None:
        """Extract from CrossRef."""
        paper = self.crossref.get_paper_from_url(url)
        if paper is None:
            return None

        year = int(paper.published[:4]) if paper.published else None

        return ExtractedMetadata(
            url=url,
            title=paper.title,
            authors=", ".join(paper.authors),
            abstract=paper.abstract,
            doi=paper.doi,
            arxiv_id=None,
            bibtex=self.crossref.generate_bibtex(paper),
            year=year,
            venue=paper.venue,
            pdf_url=None,
            source="crossref",
        )

    def _try_all_sources(self, url: str) -> ExtractedMetadata | None:
        """Try all sources to extract metadata."""
        # Try Semantic Scholar first (has good coverage)
        result = self.semantic_scholar.get_paper_from_url(url)
        if result:
            return ExtractedMetadata(
                url=url,
                title=result.title,
                authors=", ".join(result.authors),
                abstract=result.abstract,
                doi=result.doi,
                arxiv_id=result.arxiv_id,
                bibtex=self.semantic_scholar.generate_bibtex(result),
                year=result.year,
                venue=result.venue,
                pdf_url=None,
                source="semantic_scholar",
            )

        return None

    def search(self, query: str, limit: int = 10) -> list[ExtractedMetadata]:
        """Search across all sources."""
        results = []

        # Search arXiv
        arxiv_results = self.arxiv.search(query, max_results=limit // 2)
        for paper in arxiv_results:
            results.append(
                ExtractedMetadata(
                    url=f"https://arxiv.org/abs/{paper.arxiv_id}",
                    title=paper.title,
                    authors=", ".join(paper.authors),
                    abstract=paper.abstract,
                    doi=paper.doi,
                    arxiv_id=paper.arxiv_id,
                    bibtex=self.arxiv.generate_bibtex(paper),
                    year=int(paper.published[:4]) if paper.published else None,
                    venue="arXiv",
                    pdf_url=paper.pdf_url,
                    source="arxiv",
                )
            )

        # Search Semantic Scholar
        ss_results = self.semantic_scholar.search(query, limit=limit // 2)
        for paper in ss_results:
            # Skip if we already have this paper
            if any(r.doi == paper.doi and paper.doi for r in results):
                continue
            if any(r.arxiv_id == paper.arxiv_id and paper.arxiv_id for r in results):
                continue

            results.append(
                ExtractedMetadata(
                    url=paper.url or f"https://doi.org/{paper.doi}" if paper.doi else "",
                    title=paper.title,
                    authors=", ".join(paper.authors),
                    abstract=paper.abstract,
                    doi=paper.doi,
                    arxiv_id=paper.arxiv_id,
                    bibtex=self.semantic_scholar.generate_bibtex(paper),
                    year=paper.year,
                    venue=paper.venue,
                    pdf_url=None,
                    source="semantic_scholar",
                )
            )

        return results[:limit]
