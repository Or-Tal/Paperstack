"""Semantic Scholar API client."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class SemanticScholarPaper:
    """Paper metadata from Semantic Scholar."""

    paper_id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    url: str | None
    citation_count: int
    reference_count: int
    fields_of_study: list[str]
    external_ids: dict[str, str]


class SemanticScholarClient:
    """Client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    FIELDS = "paperId,title,authors,abstract,year,venue,doi,externalIds,url,citationCount,referenceCount,fieldsOfStudy"

    DOI_PATTERNS = [
        r"doi\.org/(10\.\d{4,}/[^\s]+)",
        r"(10\.\d{4,}/[^\s]+)",
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30)

    @property
    def headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @classmethod
    def extract_doi(cls, url: str) -> str | None:
        """Extract DOI from URL."""
        for pattern in cls.DOI_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parse_paper(self, data: dict[str, Any]) -> SemanticScholarPaper:
        """Parse paper data from API response."""
        external_ids = data.get("externalIds", {}) or {}
        return SemanticScholarPaper(
            paper_id=data.get("paperId", ""),
            title=data.get("title", "Unknown Title"),
            authors=[a.get("name", "") for a in data.get("authors", [])],
            abstract=data.get("abstract"),
            year=data.get("year"),
            venue=data.get("venue"),
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            url=data.get("url"),
            citation_count=data.get("citationCount", 0),
            reference_count=data.get("referenceCount", 0),
            fields_of_study=data.get("fieldsOfStudy") or [],
            external_ids=external_ids,
        )

    def get_paper_by_id(self, paper_id: str) -> SemanticScholarPaper | None:
        """Get paper by Semantic Scholar ID."""
        try:
            response = self.client.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params={"fields": self.FIELDS},
                headers=self.headers,
            )
            if response.status_code == 200:
                return self._parse_paper(response.json())
            return None
        except Exception:
            return None

    def get_paper_by_doi(self, doi: str) -> SemanticScholarPaper | None:
        """Get paper by DOI."""
        return self.get_paper_by_id(f"DOI:{doi}")

    def get_paper_by_arxiv(self, arxiv_id: str) -> SemanticScholarPaper | None:
        """Get paper by arXiv ID."""
        return self.get_paper_by_id(f"ARXIV:{arxiv_id}")

    def get_paper_from_url(self, url: str) -> SemanticScholarPaper | None:
        """Get paper from URL (DOI or Semantic Scholar)."""
        # Try DOI first
        doi = self.extract_doi(url)
        if doi:
            return self.get_paper_by_doi(doi)

        # Try Semantic Scholar URL
        if "semanticscholar.org" in url:
            match = re.search(r"/paper/[^/]+/([a-f0-9]+)", url)
            if match:
                return self.get_paper_by_id(match.group(1))

        return None

    def search(self, query: str, limit: int = 10, offset: int = 0) -> list[SemanticScholarPaper]:
        """Search for papers."""
        try:
            response = self.client.get(
                f"{self.BASE_URL}/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "offset": offset,
                    "fields": self.FIELDS,
                },
                headers=self.headers,
            )
            if response.status_code == 200:
                data = response.json()
                return [self._parse_paper(p) for p in data.get("data", [])]
            return []
        except Exception:
            return []

    def get_references(self, paper_id: str, limit: int = 50) -> list[SemanticScholarPaper]:
        """Get references for a paper."""
        try:
            response = self.client.get(
                f"{self.BASE_URL}/paper/{paper_id}/references",
                params={"limit": limit, "fields": self.FIELDS},
                headers=self.headers,
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    self._parse_paper(ref["citedPaper"])
                    for ref in data.get("data", [])
                    if ref.get("citedPaper")
                ]
            return []
        except Exception:
            return []

    def get_citations(self, paper_id: str, limit: int = 50) -> list[SemanticScholarPaper]:
        """Get citations of a paper."""
        try:
            response = self.client.get(
                f"{self.BASE_URL}/paper/{paper_id}/citations",
                params={"limit": limit, "fields": self.FIELDS},
                headers=self.headers,
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    self._parse_paper(cit["citingPaper"])
                    for cit in data.get("data", [])
                    if cit.get("citingPaper")
                ]
            return []
        except Exception:
            return []

    def generate_bibtex(self, paper: SemanticScholarPaper) -> str:
        """Generate BibTeX entry."""
        key = paper.paper_id[:20] if paper.paper_id else "unknown"
        authors = " and ".join(paper.authors)
        year = paper.year or "2024"

        bibtex = f"""@article{{{key},
  title = {{{paper.title}}},
  author = {{{authors}}},
  year = {{{year}}}"""

        if paper.venue:
            bibtex += f",\n  journal = {{{paper.venue}}}"
        if paper.doi:
            bibtex += f",\n  doi = {{{paper.doi}}}"
        if paper.arxiv_id:
            bibtex += f",\n  eprint = {{{paper.arxiv_id}}}"
            bibtex += ",\n  archivePrefix = {arXiv}"

        bibtex += "\n}"
        return bibtex
