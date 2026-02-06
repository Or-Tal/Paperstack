"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest

from paperstack.config import get_settings, reload_settings
from paperstack.db import init_db
from paperstack.db.session import get_engine


@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path, monkeypatch):
    """Automatically isolate each test with its own database.

    This fixture runs for EVERY test automatically (autouse=True).
    It ensures tests never touch the user's real database.
    """
    # Set environment variable to override home directory
    monkeypatch.setenv("PAPERSTACK_HOME_DIR", str(tmp_path))

    # Clear any cached engine/settings from previous tests
    get_engine.cache_clear()
    get_settings.cache_clear()

    # Get fresh settings pointing to temp directory
    settings = get_settings()
    settings.ensure_directories()

    # Initialize the test database
    init_db()

    yield settings

    # Cleanup
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def repo(isolated_test_db):
    """Create repository with isolated test database."""
    from paperstack.db import Repository

    repository = Repository()
    yield repository
    repository.close()
