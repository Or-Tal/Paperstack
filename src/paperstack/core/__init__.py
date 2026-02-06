"""Core module for Paperstack."""
from __future__ import annotations


from .schemas import (
    AnnotationCreate,
    AnnotationResponse,
    DoneEntryCreate,
    DoneEntryResponse,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
    SearchResult,
)

__all__ = [
    "PaperCreate",
    "PaperUpdate",
    "PaperResponse",
    "AnnotationCreate",
    "AnnotationResponse",
    "DoneEntryCreate",
    "DoneEntryResponse",
    "SearchResult",
]
