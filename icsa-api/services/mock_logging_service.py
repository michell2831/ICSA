"""Unit-test mock for ClickHouse logging — zero DB connections.

Enabled via USE_MOCK_LOGGING=true. Keeps an in-memory list so tests can
assert that logging was invoked without any ClickHouse container.
"""
from typing import List

logged: List[dict] = []


async def log_interaction(
    session_id: str,
    query_text: str,
    matched_service_id: str,
    matched_service_name: str,
    office: str,
    confidence: float,
    response_time_ms: int,
    escalated: bool,
) -> None:
    logged.append({
        "session_id": session_id,
        "query_text": query_text,
        "matched_service_id": matched_service_id,
        "matched_service_name": matched_service_name,
        "office": office,
        "confidence": confidence,
        "response_time_ms": response_time_ms,
        "escalated": escalated,
    })
