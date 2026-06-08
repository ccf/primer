"""Local sentence-transformers embeddings for memory consolidation (Plan 2b).

Vectors are generated ONLY during the nightly consolidation pass and ONLY on
postgres deployments (the embedding column is vector-typed there; absent/JSON on
SQLite). The model is loaded lazily into a module cache and reused for the
process lifetime. Privacy-first: no API, no key, fully on-prem.
"""

import logging

from primer.common.config import settings
from primer.common.database import _is_sqlite

logger = logging.getLogger(__name__)

_MODEL = None


def embeddings_available() -> bool:
    """Vector embeddings require postgres (the SQLite column is JSON, no index)."""
    return not _is_sqlite


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        kwargs = {}
        if settings.memory_model_cache_dir:
            kwargs["cache_folder"] = settings.memory_model_cache_dir
        logger.info("Loading embedding model %s", settings.memory_embedding_model)
        model = SentenceTransformer(settings.memory_embedding_model, **kwargs)
        dim = model.get_sentence_embedding_dimension()
        if dim != settings.memory_embedding_dim:
            raise RuntimeError(
                f"Embedding model {settings.memory_embedding_model} produces "
                f"{dim}-dim vectors but settings.memory_embedding_dim="
                f"{settings.memory_embedding_dim} (the MemoryEntry.embedding column "
                f"is Vector({settings.memory_embedding_dim})); they must match."
            )
        _MODEL = model
    return _MODEL


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a batch of texts. Returns None when embeddings are unavailable
    (SQLite) so callers fall back to keyword similarity."""
    if not embeddings_available() or not texts:
        return None
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [list(map(float, v)) for v in vectors]
