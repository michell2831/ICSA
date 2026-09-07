"""AI-08: RAG orchestrator unit tests (2) — mock components only."""
from services.rag_orchestrator import NO_CONTEXT_MESSAGE, RAGOrchestrator


def test_relevant_query_returns_answer():
    r = RAGOrchestrator().process_query(
        "What requirements for a medical certificate?", session_id="test-session"
    )
    assert r.answer and len(r.answer) > 10
    assert r.matched_service is not None
    assert r.response_time_ms >= 0


def test_off_topic_query_returns_fixed_message():
    # Mock store returns [] for token-less gibberish → fixed no-context message.
    r = RAGOrchestrator().process_query("12345 9999 000", session_id="test-session")
    assert r.answer == NO_CONTEXT_MESSAGE
    assert r.escalated is True


def test_matched_services_filtering():
    r = RAGOrchestrator().process_query(
        "What requirements for a medical certificate?", session_id="test-session"
    )
    assert hasattr(r, "matched_services")
    assert isinstance(r.matched_services, list)
    for ms in r.matched_services:
        assert ms.confidence >= 0.40
