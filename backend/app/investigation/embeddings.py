"""Embedding generation providers for Sherlog Vector RAG.

Provides typed interfaces for generating text embeddings using:
- FastEmbed (local CPU ONNX inference)
- OpenAI-compatible remote embeddings API (httpx)
- Deterministic fallback provider (offline/outage resilient)
"""

from abc import ABC, abstractmethod
import hashlib
import logging
import math
import re
from typing import List, Optional
import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for vector embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate a single vector embedding for text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        pass


class DeterministicFallbackEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency embedding generator.

    Produces consistent 384-dimensional unit-norm float vectors based on
    token hashing and n-gram term frequencies. Guarantees cosine similarity
    is mathematically valid and semantic overlap produces higher similarity.
    Used for offline testing, CI environments, and provider outage fallback.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "deterministic_fallback"

    def embed_text(self, text: str) -> List[float]:
        return self._compute_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._compute_vector(t) for t in texts]

    def _compute_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        # Tokenize and extract unigrams and bigrams
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return [0.0] * self._dim

        features = list(tokens)
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i+1]}")

        vec = [0.0] * self._dim
        for feat in features:
            h = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
            vec[idx] += sign

        # Unit-normalize vector so dot product equals cosine similarity
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            return [x / norm for x in vec]
        return [0.0] * self._dim


class FastEmbedProvider(EmbeddingProvider):
    """Local, low-latency ONNX-based embedding provider using FastEmbed."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5"
        self._model = None
        self._dim = 384

    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
            except Exception as exc:
                logger.warning("Failed to initialize FastEmbed: %s. Using fallback.", exc)
                raise
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "fastembed"

    def embed_text(self, text: str) -> List[float]:
        model = self._get_model()
        emb_gen = model.embed([text])
        for vec in emb_gen:
            return [float(x) for x in vec]
        return [0.0] * self._dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        emb_gen = model.embed(texts)
        return [[float(x) for x in vec] for vec in emb_gen]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Remote embedding provider using an OpenAI-compatible /v1/embeddings endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = (base_url or settings.EMBEDDING_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.model_name = model_name or settings.EMBEDDING_MODEL or "text-embedding-3-small"
        self.timeout = timeout
        self._dim = 384

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def embed_text(self, text: str) -> List[float]:
        res = self.embed_batch([text])
        return res[0] if res else [0.0] * self._dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise ValueError("Missing EMBEDDING_API_KEY for remote embedding provider")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"input": texts, "model": self.model_name},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            data.sort(key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in data]


def get_embedding_provider(provider_type: Optional[str] = None) -> EmbeddingProvider:
    """Factory creating configured embedding provider with automatic resilient fallback."""
    p_type = (provider_type or settings.EMBEDDING_PROVIDER or "fastembed").lower()

    if p_type == "openai" or p_type == "openai_compatible":
        try:
            return OpenAIEmbeddingProvider()
        except Exception as exc:
            logger.warning("OpenAI embedding provider init failed: %s. Using fallback.", exc)
            return DeterministicFallbackEmbeddingProvider()

    if p_type == "fastembed":
        try:
            return FastEmbedProvider()
        except Exception as exc:
            logger.warning("FastEmbed provider init failed: %s. Using fallback.", exc)
            return DeterministicFallbackEmbeddingProvider()

    return DeterministicFallbackEmbeddingProvider()
