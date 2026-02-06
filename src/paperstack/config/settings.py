"""Paperstack settings using Pydantic."""

from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(str, Enum):
    """Storage backend options."""
    LOCAL = "local"
    GDRIVE = "gdrive"


class ViewerMode(str, Enum):
    """PDF viewer mode options."""
    BUILTIN = "builtin"  # Built-in Flask + PDF.js viewer
    SCHOLAR = "scholar"  # Google Scholar PDF Reader Chrome extension


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="PAPERSTACK_",
        env_file=".env",
        extra="ignore",
    )

    # Paths
    home_dir: Path = Field(
        default_factory=lambda: Path.home() / ".paperstack",
        description="Paperstack data directory",
    )

    # Database
    db_name: str = Field(default="paperstack.db", description="SQLite database filename")

    # Storage
    storage_backend: StorageBackend = Field(
        default=StorageBackend.LOCAL,
        description="Storage backend for PDFs",
    )

    # Google Drive (optional)
    gdrive_folder_id: Optional[str] = Field(
        default=None,
        description="Google Drive folder ID for paper storage",
    )

    # LLM
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use",
    )
    auto_tag: bool = Field(
        default=True,
        description="Auto-generate tags when adding papers",
    )
    auto_description: bool = Field(
        default=True,
        description="Auto-generate descriptions when adding papers",
    )

    # Embeddings
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings",
    )

    # Viewer
    viewer_host: str = Field(default="127.0.0.1", description="Flask server host")
    viewer_port: int = Field(default=5000, description="Flask server port")
    viewer_mode: ViewerMode = Field(
        default=ViewerMode.BUILTIN,
        description="PDF viewer mode: builtin (Flask+PDF.js) or scholar (Chrome extension)",
    )

    # Memory
    memory_retention_days: int = Field(
        default=30,
        description="Days to retain search memory before cleanup",
    )

    # Search
    search_results_per_page: int = Field(default=5, description="Results per page")
    max_search_results: int = Field(default=50, description="Max results from external search")

    @property
    def db_path(self) -> Path:
        """Full path to the database file."""
        return self.home_dir / self.db_name

    @property
    def papers_dir(self) -> Path:
        """Directory for local PDF storage."""
        return self.home_dir / "papers"

    @property
    def annotations_dir(self) -> Path:
        """Directory for annotation JSON files."""
        return self.home_dir / "annotations"

    @property
    def config_file(self) -> Path:
        """Path to user config file."""
        return self.home_dir / "config.json"

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        self.home_dir.mkdir(parents=True, exist_ok=True)
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.annotations_dir.mkdir(parents=True, exist_ok=True)

    def save_to_file(self) -> None:
        """Save current settings to config file."""
        self.ensure_directories()
        config_data = {
            "storage_backend": self.storage_backend.value,
            "gdrive_folder_id": self.gdrive_folder_id,
            "llm_model": self.llm_model,
            "auto_tag": self.auto_tag,
            "auto_description": self.auto_description,
            "embedding_model": self.embedding_model,
            "viewer_host": self.viewer_host,
            "viewer_port": self.viewer_port,
            "viewer_mode": self.viewer_mode.value,
            "memory_retention_days": self.memory_retention_days,
            "search_results_per_page": self.search_results_per_page,
            "max_search_results": self.max_search_results,
        }
        with open(self.config_file, "w") as f:
            json.dump(config_data, f, indent=2)

    @classmethod
    def load_from_file(cls, home_dir: Optional[Path] = None) -> "Settings":
        """Load settings from config file, merging with defaults."""
        import os

        if home_dir is None:
            # Check environment variable first
            env_home = os.environ.get("PAPERSTACK_HOME_DIR")
            if env_home:
                home_dir = Path(env_home)
            else:
                home_dir = Path.home() / ".paperstack"
        config_file = home_dir / "config.json"

        file_settings: Dict[str, Any] = {}
        if config_file.exists():
            with open(config_file) as f:
                file_settings = json.load(f)

        return cls(home_dir=home_dir, **file_settings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.load_from_file()


def reload_settings() -> Settings:
    """Reload settings, clearing cache."""
    get_settings.cache_clear()
    return get_settings()
