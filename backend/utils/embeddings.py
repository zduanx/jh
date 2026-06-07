"""
Embedding utility (Voyage AI) — Phase 7A.

`vectorize_text(text) -> list[float]` turns text into a 1024-dim vector for
semantic job/resume matching. Used at WRITE time only (resume upload, job
extraction) — NOT an endpoint, NOT an MCP tool. See ADR-032.

Voyage is used over a cloud HTTP API (not a local model) because embedding runs
in a 256MB Lambda where bundling a model is hostile. voyage-3 = 1024-dim, which
must match models.job.EMBEDDING_DIM and the pgvector column.
"""

import voyageai

from config.settings import settings
from models.job import EMBEDDING_DIM

VOYAGE_MODEL = "voyage-3"  # 1024-dim (ADR-032)

_client = None


def _get_client() -> voyageai.Client:
    """Lazily create the Voyage client (reads the key at call time)."""
    global _client
    if _client is None:
        if not settings.VOYAGE_API_KEY:
            raise RuntimeError("VOYAGE_API_KEY not configured")
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


def vectorize_text(text: str, input_type: str = "document") -> list[float]:
    """
    Embed a single text into a 1024-dim vector.

    input_type: "document" for stored items (jobs, resumes) vs "query" for a
    search query — Voyage optimizes the embedding slightly per type. Default
    "document" since we embed stored content at write time.

    Returns a list[float] of length EMBEDDING_DIM. Raises on empty input or
    misconfiguration (fail loud at write time).
    """
    if not text or not text.strip():
        raise ValueError("vectorize_text: empty text")

    result = _get_client().embed([text], model=VOYAGE_MODEL, input_type=input_type)
    vec = result.embeddings[0]
    if len(vec) != EMBEDDING_DIM:
        raise RuntimeError(
            f"vectorize_text: expected dim {EMBEDDING_DIM}, got {len(vec)} "
            f"(model/column mismatch?)"
        )
    return vec
