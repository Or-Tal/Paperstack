"""Embeddings module for semantic search."""
from __future__ import annotations


from .encoder import EmbeddingEncoder, get_encoder
from .search import SemanticSearch

__all__ = ["EmbeddingEncoder", "SemanticSearch", "get_encoder"]
