"""AI-03: pgvector store + cosine similarity retrieval.

Threshold rule: if the best match scores below SIMILARITY_THRESHOLD, return []
so the orchestrator answers with the fixed no-context message (no hallucination).
"""
from typing import List

import psycopg2
import psycopg2.extras

from services.embedding_service import generate_embedding
from utils import config

SIMILARITY_THRESHOLD = 0.30


def _connect():
    return psycopg2.connect(config.PGVECTOR_URL)


def _to_pgvector(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def store_embeddings(services: List[dict]) -> None:
    """Bulk upsert service embeddings. Idempotent (ON CONFLICT DO UPDATE)
    so the nightly re-index (DE-07) can run repeatedly without duplicates."""
    sql = """
        INSERT INTO service_embeddings (service_id, service_name, office, text_chunk, sla_target_value, sla_target_unit, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
        ON CONFLICT (service_id) DO UPDATE SET
            service_name = EXCLUDED.service_name,
            office = EXCLUDED.office,
            text_chunk = EXCLUDED.text_chunk,
            sla_target_value = EXCLUDED.sla_target_value,
            sla_target_unit = EXCLUDED.sla_target_unit,
            embedding = EXCLUDED.embedding
    """
    rows = [
        (
            str(s["id"]),
            s.get("name") or s.get("service_name"),
            s.get("office"),
            s["text_chunk"],
            s.get("sla_target_value"),
            s.get("sla_target_unit"),
            _to_pgvector(s["embedding"]),
        )
        for s in services
    ]
    with _connect() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)


def search_similar(query_text: str, top_k: int = 3) -> List[dict]:
    """Embed the query locally, then cosine-search pgvector."""
    query_vec = _to_pgvector(generate_embedding(query_text))
    sql = """
        SELECT service_id, service_name, office, text_chunk, sla_target_value, sla_target_unit,
               1 - (embedding <=> %s::vector) AS similarity
        FROM service_embeddings
        ORDER BY similarity DESC
        LIMIT %s
    """
    with _connect() as conn, conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        cur.execute(sql, (query_vec, top_k))
        results = [dict(r) for r in cur.fetchall()]

    if not results or float(results[0]["similarity"]) < SIMILARITY_THRESHOLD:
        return []  # below threshold — no-context response, never hallucinate
    return [r for r in results if float(r["similarity"]) >= SIMILARITY_THRESHOLD]