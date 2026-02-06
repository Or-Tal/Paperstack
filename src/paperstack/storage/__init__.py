"""Storage backends for Paperstack."""
from __future__ import annotations


from .base import StorageBackend
from .local import LocalStorage

__all__ = ["StorageBackend", "LocalStorage"]
