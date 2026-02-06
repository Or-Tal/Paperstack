"""Abstract storage backend interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save_pdf(self, paper_id: int, content: bytes | BinaryIO) -> str:
        """Save a PDF and return the storage path/identifier."""
        pass

    @abstractmethod
    def get_pdf(self, path: str) -> bytes | None:
        """Get PDF content by path/identifier."""
        pass

    @abstractmethod
    def get_pdf_path(self, path: str) -> Path | str | None:
        """Get local path to PDF (downloads if needed for remote backends)."""
        pass

    @abstractmethod
    def delete_pdf(self, path: str) -> bool:
        """Delete a PDF."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a PDF exists."""
        pass
