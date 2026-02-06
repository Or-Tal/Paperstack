"""Sentence transformer encoder for embeddings."""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

from paperstack.config import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingEncoder:
    """Encoder using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> "SentenceTransformer":
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text to embedding."""
        return self.model.encode(text, convert_to_numpy=True)

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Encode multiple texts to embeddings."""
        return self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True)

    def to_bytes(self, embedding: np.ndarray) -> bytes:
        """Convert embedding to bytes for storage."""
        return embedding.astype(np.float32).tobytes()

    def from_bytes(self, data: bytes) -> np.ndarray:
        """Convert bytes back to embedding."""
        return np.frombuffer(data, dtype=np.float32)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def cosine_similarity_batch(
        self, query: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between query and batch of embeddings."""
        # Normalize query
        query_norm = query / np.linalg.norm(query)
        # Normalize embeddings (assuming shape: N x dim)
        emb_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_norm = embeddings / emb_norms
        # Compute similarities
        return np.dot(embeddings_norm, query_norm)


@lru_cache
def get_encoder() -> EmbeddingEncoder:
    """Get cached encoder instance."""
    return EmbeddingEncoder()
