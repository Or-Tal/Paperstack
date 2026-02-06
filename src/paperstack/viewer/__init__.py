"""PDF viewer module with Flask server."""
from __future__ import annotations


from .server import create_app, run_viewer

__all__ = ["create_app", "run_viewer"]
