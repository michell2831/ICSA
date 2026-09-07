"""AI-12: Async fire-and-forget ClickHouse logging (real implementation).

Routing: USE_MOCK_LOGGING=true → services.mock_logging_service (no DB import).
A logging failure must NEVER break /api/chat (catch-all, print only).
"""
import asyncio
import uuid
from datetime import datetime

from utils import config


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
    if config.USE_MOCK_LOGGING:
        from services.mock_logging_service import log_interaction as mock_log
        await mock_log(
            session_id, query_text, matched_service_id, matched_service_name,
            office, confidence, response_time_ms, escalated,
        )
        return

    try:
        await asyncio.to_thread(
            _insert_row,
            session_id, query_text, matched_service_id,
            matched_service_name, office, confidence,
            response_time_ms, escalated,
        )
    except Exception as e:  # noqa: BLE001 — logging must be failure-safe
        print(f"[LOGGING ERROR] ClickHouse unavailable: {e}")


def _insert_row(
    session_id, query_text, matched_service_id, matched_service_name,
    office, confidence, response_time_ms, escalated,
):
    from clickhouse_driver import Client  # lazy import (mock mode never touches this)

    client = Client(
        host=config.CLICKHOUSE_HOST,
        user="default",
        password=config.CLICKHOUSE_PASSWORD,
    )
    client.execute(
        "INSERT INTO icsa.interaction_logs "
        "(id, session_id, query_text, matched_service_id, matched_service_name, "
        " office, confidence, response_time_ms, escalated, created_at) VALUES",
        [{
            "id": uuid.uuid4(),
            "session_id": session_id or "",
            "query_text": query_text,
            "matched_service_id": matched_service_id or "",
            "matched_service_name": matched_service_name or "",
            "office": office or "",
            "confidence": float(confidence),
            "response_time_ms": int(response_time_ms),
            "escalated": 1 if escalated else 0,
            "created_at": datetime.now(),
        }],
    )