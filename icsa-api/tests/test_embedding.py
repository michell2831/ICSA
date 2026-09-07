"""AI-08: embedding unit tests (2). Requires sentence-transformers installed;
first run downloads all-MiniLM-L6-v2 (~90MB), then it loads from local cache."""
import pytest

pytest.importorskip("sentence_transformers", reason="Install: pip install sentence-transformers")

from services.embedding_service import generate_embedding, generate_embeddings_batch


def test_single_embedding_is_384_floats():
    vec = generate_embedding("Medical Certificate")
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
    assert all(-1.0 <= x <= 1.0 for x in vec)


def test_batch_embedding_fixture(fixture_services):
    texts = [s["name"] for s in fixture_services]
    vecs = generate_embeddings_batch(texts)
    assert len(vecs) == len(fixture_services)
    assert all(len(v) == 384 for v in vecs)
