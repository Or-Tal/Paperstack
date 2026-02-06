"""Pydantic schemas for API/CLI data transfer."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class PaperCreate(BaseModel):
    """Schema for creating a new paper."""

    url: str
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    bibtex: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    pdf_path: Optional[str] = None


class PaperUpdate(BaseModel):
    """Schema for updating a paper."""

    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    bibtex: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    status: Optional[str] = None
    pdf_path: Optional[str] = None


class PaperResponse(BaseModel):
    """Schema for paper response."""

    id: int
    url: str
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    bibtex: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    status: str
    pdf_path: Optional[str] = None
    added_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: Any) -> List[str]:
        """Parse tags from JSON string or list."""
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    class Config:
        from_attributes = True


class AnnotationCreate(BaseModel):
    """Schema for creating an annotation."""

    page: int
    type: str  # highlight, comment, note
    content: Optional[str] = None
    selection_text: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    color: str = "#ffeb3b"


class AnnotationResponse(BaseModel):
    """Schema for annotation response."""

    id: int
    paper_id: int
    page: int
    type: str
    content: Optional[str] = None
    selection_text: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    color: str
    created_at: datetime

    @field_validator("position", mode="before")
    @classmethod
    def parse_position(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Parse position from JSON string or dict."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    class Config:
        from_attributes = True


class DoneEntryCreate(BaseModel):
    """Schema for marking a paper as done."""

    concepts: List[str] = Field(default_factory=list)


class DoneEntryResponse(BaseModel):
    """Schema for done entry response."""

    id: int
    paper_id: int
    user_concepts: List[str] = Field(default_factory=list)
    compressed_summary: Optional[str] = None
    key_contributions: Optional[str] = None
    completed_at: datetime

    @field_validator("user_concepts", mode="before")
    @classmethod
    def parse_concepts(cls, v: Any) -> List[str]:
        """Parse concepts from JSON string or list."""
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Schema for search result."""

    paper: PaperResponse
    score: float
    summary: Optional[str] = None
    matched_content: Optional[str] = None


class ExternalPaper(BaseModel):
    """Schema for paper from external search."""

    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    source: str  # semantic_scholar, arxiv, crossref


class SearchResultPage(BaseModel):
    """Schema for paginated search results."""

    results: List[Union[SearchResult, ExternalPaper]]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
