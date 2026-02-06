"""Local filesystem storage backend."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from paperstack.config import get_settings

from .base import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage for PDFs."""

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            settings = get_settings()
            base_dir = settings.papers_dir
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, paper_id: int) -> Path:
        """Get the local path for a paper PDF."""
        return self.base_dir / f"{paper_id}.pdf"

    def save_pdf(self, paper_id: int, content: bytes | BinaryIO) -> str:
        """Save a PDF to local storage."""
        path = self._get_path(paper_id)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_bytes(content.read())
        return str(path)

    def get_pdf(self, path: str) -> bytes | None:
        """Get PDF content from local storage."""
        p = Path(path)
        if p.exists():
            return p.read_bytes()
        return None

    def get_pdf_path(self, path: str) -> Path | None:
        """Get local path to PDF."""
        p = Path(path)
        if p.exists():
            return p
        return None

    def delete_pdf(self, path: str) -> bool:
        """Delete a PDF from local storage."""
        p = Path(path)
        if p.exists():
            p.unlink()
            return True
        return False

    def exists(self, path: str) -> bool:
        """Check if a PDF exists in local storage."""
        return Path(path).exists()
