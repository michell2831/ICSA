"""AI-02: Embedding module — sentence-transformers all-MiniLM-L6-v2 (384 dims).

IMPORTANT: This LOCAL model generates the embeddings. Groq/Llama is never
called here (Groq is only used for answer generation in llm_service.py).

The model is a lazy singleton: loaded once on first use, cached afterwards.
"""
from typing import List

from utils import config

_model = None  # singleton — do NOT reload per request


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # lazy import
        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def generate_embedding(text: str) -> List[float]:
    """Embed one text. Returns exactly 384 floats."""
    vec = _get_model().encode(text, normalize_embeddings=True)
    return [float(x) for x in vec]


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Embed many texts safely with torch.no_grad and small batch size to stay under 512MB RAM."""
    try:
        import torch
        with torch.no_grad():
            vecs = _get_model().encode(
                texts,
                normalize_embeddings=True,
                batch_size=8,
                show_progress_bar=False,
            )
    except Exception:
        vecs = _get_model().encode(
            texts,
            normalize_embeddings=True,
            batch_size=8,
            show_progress_bar=False,
        )
    return [[float(x) for x in v] for v in vecs]
