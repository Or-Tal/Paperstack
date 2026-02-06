"""Tests for configuration."""

import json
import tempfile
from pathlib import Path

import pytest

from paperstack.config import Settings, StorageBackend


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.storage_backend == StorageBackend.LOCAL
        assert settings.llm_model == "claude-sonnet-4-20250514"
        assert settings.auto_tag is True
        assert settings.viewer_port == 5000

    def test_db_path(self):
        """Test database path property."""
        settings = Settings()
        assert settings.db_path == settings.home_dir / "paperstack.db"

    def test_papers_dir(self):
        """Test papers directory property."""
        settings = Settings()
        assert settings.papers_dir == settings.home_dir / "papers"

    def test_ensure_directories(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(home_dir=Path(tmpdir) / "paperstack")
            settings.ensure_directories()

            assert settings.home_dir.exists()
            assert settings.papers_dir.exists()
            assert settings.annotations_dir.exists()

    def test_save_and_load(self):
        """Test saving and loading settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                home_dir=Path(tmpdir),
                viewer_port=8080,
                auto_tag=False,
            )
            settings.save_to_file()

            # Load settings
            loaded = Settings.load_from_file(Path(tmpdir))
            assert loaded.viewer_port == 8080
            assert loaded.auto_tag is False
