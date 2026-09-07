"""AI-06: POST /api/chat — the citizen-facing chatbot endpoint."""
import time
import traceback
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.request_models import ChatRequest
from models.response_models import ChatResponse
from services.rag_orchestrator import RAGOrchestrator

router = APIRouter()
_orchestrator = RAGOrchestrator()


@router.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    start = time.time()

    if not body.query or not body.query.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Query cannot be empty", "code": 400},
        )

    session_id = body.session_id or str(uuid4())

    history = (
        [turn.model_dump() for turn in body.chat_history]
        if body.chat_history
        else []
    )

    try:
        response = _orchestrator.process_query(body.query, session_id, history)
        response.response_time_ms = int((time.time() - start) * 1000)
        response.session_id = session_id
        return response
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "Query cannot be empty", "code": 400},
        )
    except Exception as e:
        traceback.print_exc()
        return ChatResponse(
            answer=(
                "I'm here to assist with official PUP Caloocan campus services. "
                "Please ask your question again or visit the concerned campus office."
            ),
            session_id=session_id,
            response_time_ms=int((time.time() - start) * 1000),
            confidence=0.5,
            escalated=True,
        )