"""arXiv API client for paper metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import arxiv


@dataclass
class ArxivPaper:
    """Paper metadata from arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    updated: str
    pdf_url: str
    doi: str | None
    categories: list[str]


class ArxivClient:
    """Client for arXiv API."""

    ARXIV_URL_PATTERNS = [
        r"arxiv\.org/abs/(\d+\.\d+)",
        r"arxiv\.org/pdf/(\d+\.\d+)",
        r"arxiv\.org/abs/([a-z-]+/\d+)",
        r"arxiv:(\d+\.\d+)",
    ]

    def __init__(self):
        self.client = arxiv.Client()

    @classmethod
    def extract_arxiv_id(cls, url: str) -> str | None:
        """Extract arXiv ID from URL."""
        for pattern in cls.ARXIV_URL_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @classmethod
    def is_arxiv_url(cls, url: str) -> bool:
        """Check if URL is an arXiv URL."""
        return cls.extract_arxiv_id(url) is not None

    def get_paper(self, arxiv_id: str) -> ArxivPaper | None:
        """Get paper metadata by arXiv ID."""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(self.client.results(search))
            if not results:
                return None

            paper = results[0]
            return ArxivPaper(
                arxiv_id=paper.entry_id.split("/")[-1].replace("v", ".v")
                if "v" in paper.entry_id
                else paper.entry_id.split("/")[-1],
                title=paper.title,
                authors=[author.name for author in paper.authors],
                abstract=paper.summary,
                published=paper.published.isoformat(),
                updated=paper.updated.isoformat() if paper.updated else paper.published.isoformat(),
                pdf_url=paper.pdf_url,
                doi=paper.doi,
                categories=paper.categories,
            )
        except Exception:
            return None

    def get_paper_from_url(self, url: str) -> ArxivPaper | None:
        """Get paper metadata from arXiv URL."""
        arxiv_id = self.extract_arxiv_id(url)
        if arxiv_id is None:
            return None
        return self.get_paper(arxiv_id)

    def search(self, query: str, max_results: int = 10) -> list[ArxivPaper]:
        """Search for papers on arXiv."""
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            papers = []
            for paper in self.client.results(search):
                papers.append(
                    ArxivPaper(
                        arxiv_id=paper.entry_id.split("/")[-1],
                        title=paper.title,
                        authors=[author.name for author in paper.authors],
                        abstract=paper.summary,
                        published=paper.published.isoformat(),
                        updated=paper.updated.isoformat()
                        if paper.updated
                        else paper.published.isoformat(),
                        pdf_url=paper.pdf_url,
                        doi=paper.doi,
                        categories=paper.categories,
                    )
                )
            return papers
        except Exception:
            return []

    def download_pdf(self, arxiv_id: str) -> bytes | None:
        """Download PDF for a paper."""
        try:
            import httpx

            paper = self.get_paper(arxiv_id)
            if paper is None:
                return None

            response = httpx.get(paper.pdf_url, follow_redirects=True, timeout=60)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None

    def generate_bibtex(self, paper: ArxivPaper) -> str:
        """Generate BibTeX entry for an arXiv paper."""
        arxiv_id_clean = paper.arxiv_id.replace(".", "_").replace("/", "_")
        authors = " and ".join(paper.authors)
        year = paper.published[:4] if paper.published else "2024"

        return f"""@article{{{arxiv_id_clean},
  title = {{{paper.title}}},
  author = {{{authors}}},
  journal = {{arXiv preprint arXiv:{paper.arxiv_id}}},
  year = {{{year}}},
  eprint = {{{paper.arxiv_id}}},
  archivePrefix = {{arXiv}},
  primaryClass = {{{paper.categories[0] if paper.categories else "cs.LG"}}}
}}"""
