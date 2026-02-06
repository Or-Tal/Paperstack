"""Tests for metadata extraction."""

import pytest

from paperstack.metadata import ArxivClient, SemanticScholarClient, CrossRefClient


class TestArxivClient:
    """Test arXiv client."""

    def test_extract_arxiv_id_from_abs_url(self):
        """Test extracting arXiv ID from abs URL."""
        client = ArxivClient()
        arxiv_id = client.extract_arxiv_id("https://arxiv.org/abs/2301.07041")
        assert arxiv_id == "2301.07041"

    def test_extract_arxiv_id_from_pdf_url(self):
        """Test extracting arXiv ID from PDF URL."""
        client = ArxivClient()
        arxiv_id = client.extract_arxiv_id("https://arxiv.org/pdf/2301.07041.pdf")
        assert arxiv_id == "2301.07041"

    def test_is_arxiv_url(self):
        """Test arXiv URL detection."""
        assert ArxivClient.is_arxiv_url("https://arxiv.org/abs/2301.07041")
        assert ArxivClient.is_arxiv_url("https://arxiv.org/pdf/2301.07041")
        assert not ArxivClient.is_arxiv_url("https://example.com")


class TestSemanticScholarClient:
    """Test Semantic Scholar client."""

    def test_extract_doi(self):
        """Test DOI extraction."""
        doi = SemanticScholarClient.extract_doi("https://doi.org/10.1234/test")
        assert doi == "10.1234/test"

    def test_extract_doi_from_plain(self):
        """Test DOI extraction from plain DOI."""
        doi = SemanticScholarClient.extract_doi("10.1234/test.paper")
        assert doi == "10.1234/test.paper"


class TestCrossRefClient:
    """Test CrossRef client."""

    def test_extract_doi(self):
        """Test DOI extraction."""
        doi = CrossRefClient.extract_doi("https://doi.org/10.1000/test123")
        assert doi == "10.1000/test123"
