"""CrossRef API client."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CrossRefPaper:
    """Paper metadata from CrossRef."""

    doi: str
    title: str
    authors: list[str]
    abstract: str | None
    published: str | None
    venue: str | None
    publisher: str | None
    url: str | None
    reference_count: int
    is_referenced_by_count: int


class CrossRefClient:
    """Client for CrossRef API."""

    BASE_URL = "https://api.crossref.org/works"

    DOI_PATTERNS = [
        r"doi\.org/(10\.\d{4,}/[^\s]+)",
        r"(10\.\d{4,}/[^\s]+)",
    ]

    def __init__(self, mailto: str | None = None):
        """Initialize client with optional mailto for polite pool."""
        self.mailto = mailto
        self.client = httpx.Client(timeout=30)

    @property
    def headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.mailto:
            headers["User-Agent"] = f"Paperstack/0.1.0 (mailto:{self.mailto})"
        return headers

    @classmethod
    def extract_doi(cls, url: str) -> str | None:
        """Extract DOI from URL."""
        for pattern in cls.DOI_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parse_paper(self, data: dict[str, Any]) -> CrossRefPaper:
        """Parse paper data from API response."""
        # Extract authors
        authors = []
        for author in data.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        # Extract title
        titles = data.get("title", ["Unknown Title"])
        title = titles[0] if titles else "Unknown Title"

        # Extract abstract
        abstract = data.get("abstract")
        if abstract:
            # Remove JATS/HTML tags
            abstract = re.sub(r"<[^>]+>", "", abstract)

        # Extract published date
        published = None
        date_parts = data.get("published", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            published = "-".join(str(p) for p in parts)

        # Extract venue
        container = data.get("container-title", [])
        venue = container[0] if container else None

        return CrossRefPaper(
            doi=data.get("DOI", ""),
            title=title,
            authors=authors,
            abstract=abstract,
            published=published,
            venue=venue,
            publisher=data.get("publisher"),
            url=data.get("URL"),
            reference_count=data.get("reference-count", 0),
            is_referenced_by_count=data.get("is-referenced-by-count", 0),
        )

    def get_paper_by_doi(self, doi: str) -> CrossRefPaper | None:
        """Get paper by DOI."""
        try:
            response = self.client.get(
                f"{self.BASE_URL}/{doi}",
                headers=self.headers,
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_paper(data.get("message", {}))
            return None
        except Exception:
            return None

    def get_paper_from_url(self, url: str) -> CrossRefPaper | None:
        """Get paper from DOI URL."""
        doi = self.extract_doi(url)
        if doi:
            return self.get_paper_by_doi(doi)
        return None

    def search(
        self,
        query: str,
        rows: int = 10,
        offset: int = 0,
        sort: str = "relevance",
    ) -> list[CrossRefPaper]:
        """Search for papers."""
        try:
            response = self.client.get(
                self.BASE_URL,
                params={
                    "query": query,
                    "rows": rows,
                    "offset": offset,
                    "sort": sort,
                },
                headers=self.headers,
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])
                return [self._parse_paper(item) for item in items]
            return []
        except Exception:
            return []

    def generate_bibtex(self, paper: CrossRefPaper) -> str:
        """Generate BibTeX entry."""
        doi_key = paper.doi.replace("/", "_").replace(".", "_")[:30]
        authors = " and ".join(paper.authors)
        year = paper.published[:4] if paper.published else "2024"

        bibtex = f"""@article{{{doi_key},
  title = {{{paper.title}}},
  author = {{{authors}}},
  year = {{{year}}}"""

        if paper.venue:
            bibtex += f",\n  journal = {{{paper.venue}}}"
        if paper.doi:
            bibtex += f",\n  doi = {{{paper.doi}}}"
        if paper.url:
            bibtex += f",\n  url = {{{paper.url}}}"
        if paper.publisher:
            bibtex += f",\n  publisher = {{{paper.publisher}}}"

        bibtex += "\n}"
        return bibtex
