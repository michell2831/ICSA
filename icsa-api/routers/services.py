"""Live PSS service catalogue + on-demand re-index API.

Data source is the REAL PSS database (read-only) — not mock data.
The fixture file is only used by unit tests, never by these endpoints.
"""
import datetime
import threading

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services import pss_service
from utils.config import ConfigError

router = APIRouter()

# In-memory status of the last reindex run (simple, single-process)
_reindex_state = {"status": "never_run", "detail": None, "started_at": None, "finished_at": None}
_reindex_lock = threading.Lock()


@router.get("/api/services")
def list_services(office: str | None = None, limit: int = Query(100, ge=1, le=500)):
    """Live list of active services straight from the PSS DB (SELECT-only)."""
    try:
        services = pss_service.fetch_active_services(office=office, limit=limit)
        return {"count": len(services), "services": services}
    except ConfigError as e:
        return JSONResponse(status_code=503, content={"error": str(e), "code": 503})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=502,
            content={"error": f"PSS database unreachable: {e}", "code": 502},
        )


@router.get("/api/services/count")
def services_count():
    """Total + per-office counts from PSS (used for DE-08 validation)."""
    try:
        return pss_service.count_active_services()
    except ConfigError as e:
        return JSONResponse(status_code=503, content={"error": str(e), "code": 503})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=502,
            content={"error": f"PSS database unreachable: {e}", "code": 502},
        )


def _run_reindex() -> None:
    """Extract all active services from PSS → embed → upsert into pgvector."""
    from services.embedding_service import generate_embeddings_batch
    from services.vector_store import store_embeddings

    _reindex_state.update(
        status="running", detail=None,
        started_at=datetime.datetime.now().isoformat(), finished_at=None,
    )
    try:
        raw = pss_service.fetch_active_services()
        records = [pss_service.to_embedding_record(s) for s in raw]
        texts = [r["text_chunk"] for r in records]
        embeddings = generate_embeddings_batch(texts)
        for i, rec in enumerate(records):
            rec["embedding"] = embeddings[i]
        store_embeddings(records)
        _reindex_state.update(
            status="done",
            detail=f"Upserted {len(records)} services from PSS into pgvector.",
            finished_at=datetime.datetime.now().isoformat(),
        )
    except Exception as e:  # noqa: BLE001
        _reindex_state.update(
            status="failed", detail=str(e),
            finished_at=datetime.datetime.now().isoformat(),
        )


@router.post("/api/admin/reindex", status_code=202)
def trigger_reindex():
    """On-demand version of the nightly cron: PSS → embeddings → pgvector.

    Runs in the background (embedding 70+ services takes ~1-3 minutes on the
    first run because the model has to load). Poll /api/admin/reindex/status.
    """
    if not _reindex_lock.acquire(blocking=False):
        return JSONResponse(
            status_code=409,
            content={"error": "A reindex is already running", "code": 409},
        )

    def worker():
        try:
            _run_reindex()
        finally:
            _reindex_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "started", "check": "/api/admin/reindex/status"}


@router.get("/api/admin/reindex/status")
def reindex_status():
    return _reindex_state
