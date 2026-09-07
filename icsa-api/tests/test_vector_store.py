"""AI-08: vector store unit tests (2) — run against the MOCK store (no DB)."""
from services import mock_vector_store


def test_mock_search_returns_results_without_db():
    results = mock_vector_store.search_similar("how to get medical certificate", top_k=3)
    assert len(results) == 3
    assert results[0]["similarity"] > 0.30
    assert {"service_id", "service_name", "office", "text_chunk", "similarity"} <= set(results[0])


def test_store_embeddings_mock_is_noop(fixture_services):
    # Mock store accepts the full 15-service fixture without a DB connection.
    assert mock_vector_store.store_embeddings(fixture_services) is None
