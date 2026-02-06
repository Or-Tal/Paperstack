"""Tests for database models and repository."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from paperstack.db import Repository
from paperstack.db.models import PaperStatus


# Note: repo fixture is provided by conftest.py with isolated test database


class TestPaperOperations:
    """Test paper CRUD operations."""

    def test_add_paper(self, repo):
        """Test adding a paper."""
        paper = repo.add_paper(
            url="https://arxiv.org/abs/2301.07041",
            title="Test Paper",
            authors="Author One, Author Two",
            abstract="This is a test abstract.",
            arxiv_id="2301.07041",
            tags=["test", "machine learning"],
        )

        assert paper.id is not None
        assert paper.title == "Test Paper"
        assert paper.status == PaperStatus.READING.value
        assert json.loads(paper.tags) == ["test", "machine learning"]

    def test_get_paper(self, repo):
        """Test retrieving a paper."""
        paper = repo.add_paper(
            url="https://example.com/paper",
            title="Test Paper",
        )

        retrieved = repo.get_paper(paper.id)
        assert retrieved is not None
        assert retrieved.title == "Test Paper"

    def test_get_paper_by_url(self, repo):
        """Test retrieving paper by URL."""
        paper = repo.add_paper(
            url="https://unique-url.com/paper",
            title="URL Test",
        )

        retrieved = repo.get_paper_by_url("https://unique-url.com/paper")
        assert retrieved is not None
        assert retrieved.id == paper.id

    def test_list_papers(self, repo):
        """Test listing papers."""
        repo.add_paper(url="https://example.com/1", title="Paper 1")
        repo.add_paper(url="https://example.com/2", title="Paper 2")

        papers = repo.list_papers()
        assert len(papers) == 2

    def test_list_reading(self, repo):
        """Test listing reading papers."""
        paper1 = repo.add_paper(url="https://example.com/1", title="Reading Paper")
        paper2 = repo.add_paper(url="https://example.com/2", title="Done Paper")

        # Mark one as done
        repo.mark_done(paper2.id, user_concepts=["test"])

        reading = repo.list_reading()
        assert len(reading) == 1
        assert reading[0].id == paper1.id

    def test_update_paper(self, repo):
        """Test updating a paper."""
        paper = repo.add_paper(url="https://example.com", title="Original")

        updated = repo.update_paper(
            paper.id,
            title="Updated Title",
            tags=["new", "tags"],
        )

        assert updated.title == "Updated Title"
        assert json.loads(updated.tags) == ["new", "tags"]

    def test_delete_paper(self, repo):
        """Test deleting a paper."""
        paper = repo.add_paper(url="https://example.com", title="To Delete")

        success = repo.delete_paper(paper.id)
        assert success

        retrieved = repo.get_paper(paper.id)
        assert retrieved is None


class TestAnnotationOperations:
    """Test annotation operations."""

    def test_add_annotation(self, repo):
        """Test adding an annotation."""
        paper = repo.add_paper(url="https://example.com", title="Test")

        annotation = repo.add_annotation(
            paper_id=paper.id,
            page=1,
            annotation_type="highlight",
            selection_text="Important text",
            color="#ffeb3b",
        )

        assert annotation.id is not None
        assert annotation.type == "highlight"

    def test_get_annotations(self, repo):
        """Test getting annotations."""
        paper = repo.add_paper(url="https://example.com", title="Test")

        repo.add_annotation(paper.id, 1, "highlight", selection_text="Text 1")
        repo.add_annotation(paper.id, 2, "comment", content="Comment 1")

        annotations = repo.get_annotations(paper.id)
        assert len(annotations) == 2

    def test_delete_annotation(self, repo):
        """Test deleting an annotation."""
        paper = repo.add_paper(url="https://example.com", title="Test")
        annotation = repo.add_annotation(paper.id, 1, "highlight")

        success = repo.delete_annotation(annotation.id)
        assert success

        annotations = repo.get_annotations(paper.id)
        assert len(annotations) == 0


class TestDoneOperations:
    """Test done entry operations."""

    def test_mark_done(self, repo):
        """Test marking paper as done."""
        paper = repo.add_paper(url="https://example.com", title="Test")

        done_entry = repo.mark_done(
            paper.id,
            user_concepts=["concept1", "concept2"],
            compressed_summary="This paper is about testing.",
        )

        assert done_entry is not None
        assert json.loads(done_entry.user_concepts) == ["concept1", "concept2"]

        # Paper status should be updated
        updated_paper = repo.get_paper(paper.id)
        assert updated_paper.status == PaperStatus.DONE.value

    def test_get_done_entry(self, repo):
        """Test getting done entry."""
        paper = repo.add_paper(url="https://example.com", title="Test")
        repo.mark_done(paper.id, user_concepts=["test"])

        entry = repo.get_done_entry(paper.id)
        assert entry is not None


class TestPreferenceOperations:
    """Test preference operations."""

    def test_set_and_get_preference(self, repo):
        """Test setting and getting preferences."""
        repo.set_preference("test_key", "test_value")

        value = repo.get_preference("test_key")
        assert value == "test_value"

    def test_get_all_preferences(self, repo):
        """Test getting all preferences."""
        repo.set_preference("key1", "value1")
        repo.set_preference("key2", "value2")

        prefs = repo.get_all_preferences()
        assert prefs == {"key1": "value1", "key2": "value2"}

    def test_delete_preference(self, repo):
        """Test deleting preference."""
        repo.set_preference("to_delete", "value")

        success = repo.delete_preference("to_delete")
        assert success

        value = repo.get_preference("to_delete")
        assert value is None
