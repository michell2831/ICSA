"""AI-01: ICSA Citizen Assistant API - FastAPI entrypoint.

Run locally:  uvicorn main:app --reload
Swagger UI:   http://localhost:8000/docs
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import analytics, chat, pss_cloud_api, services
from services.embedding_service import _get_model

# Explicit setup, not left to uvicorn's defaults - guarantees logger.info()
# calls throughout the app (e.g. rag_orchestrator's per-query similarity
# score log) actually reach the console / `docker logs -f icsa-api`,
# regardless of how the app happens to be launched.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Eagerly load the SentenceTransformer model at startup.

    Without this, the model loads lazily on the first /api/chat request,
    taking 20-60 s inside Docker - long enough to blow the 25 s pipeline
    timeout and return the 'took too long' error to the first user.

    A 120-second timeout guards against the model freezing on startup
    (e.g., after a laptop sleep/wake cycle corrupts Docker networking).
    If it times out, the model will load lazily on the first request instead.
    """
    logger.info("[startup] Loading embedding model '%s' ", "all-MiniLM-L6-v2")
    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, _get_model),
            timeout=120,
        )
        logger.info("[startup] Embedding model ready.")
    except asyncio.TimeoutError:
        logger.warning(
            "[startup] Embedding model load timed out after 120 s - "
            "will load lazily on first /api/chat request."
        )
    yield
    # Shutdown logic (if any) would go here


app = FastAPI(
    title="ICSA Citizen Assistant API",
    description=(
        "RAG chatbot microservice for PUP Caloocan (PSS ICSA enhancement). "
        "Sidecar architecture - the legacy PSS system is never modified (No-Touch)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow all origins so Vercel frontend, local dev, and preview deployments connect cleanly
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# AI-06 fix: FastAPI/Pydantic's default 422 response for request-body
# validation failures (e.g. a query over the 500-char limit) looks like
# {"detail": [...]}, which doesn't match the app's standardized error
# format documented in docs/api-contracts.md: {"error": str, "code": int}.
# Every other error path in the app (400/500/503/502) already uses that
# shape - this handler normalizes the one gap so it's consistent
# everywhere, for every endpoint, without touching each router.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    field_path = ".".join(
        str(part) for part in first_error.get("loc", []) if part != "body"
    )
    message = first_error.get("msg", "Invalid request")
    error_text = f"{field_path}: {message}" if field_path else message
    return JSONResponse(status_code=400, content={"error": error_text, "code": 400})


app.include_router(chat.router, tags=["chat"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(services.router, tags=["services"])
app.include_router(pss_cloud_api.router, tags=["pss_cloud"])


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": "1.0.0"}