"""Metadata extraction module."""
from __future__ import annotations


from .arxiv_client import ArxivClient
from .crossref_client import CrossRefClient
from .extractor import MetadataExtractor
from .semantic_scholar import SemanticScholarClient

__all__ = [
    "MetadataExtractor",
    "ArxivClient",
    "SemanticScholarClient",
    "CrossRefClient",
]
