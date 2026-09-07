"""AI-05: RAG orchestration - query -> embed -> search -> LLM -> log -> response.

Flag-based routing (kept for Week 2 AI-10 - do NOT delete the mock imports;
unit tests depend on them):
    USE_MOCK_VECTOR_STORE -> services.mock_vector_store
    USE_MOCK_LLM          -> services.mock_llm_service
"""
import asyncio
import logging
import time
from typing import List, Optional

from models.response_models import ChatResponse, MatchedService
from services import logging_service
from utils import config
from utils.prompts import check_response_uses_context
from utils.query_preprocessing import (
    detect_office_query,
    expand_query,
    is_aggregate_count_query,
)

logger = logging.getLogger(__name__)

NO_CONTEXT_MESSAGE = (
    "I don't have specific information about that service. "
    "Please visit the concerned office or call PUP Caloocan at (02) 8365-0080."
)
TIMEOUT_MESSAGE = (
    "Sorry, the assistant took too long to respond. Please try again in a moment "
    "or visit the concerned office directly."
)
OFF_TOPIC_MESSAGE = (
    "I'm here to help with PUP Caloocan Citizen's Charter services! "
    "Try asking me about enrollment, ID requests, medical certificates, or another "
    "specific service you need."
)
ESCALATION_CONFIDENCE_THRESHOLD = 0.50
PIPELINE_TIMEOUT_SECONDS = 45 
MAX_QUERY_LENGTH = 500
HISTORY_TURNS_FOR_REWRITE = 5


def _search(query: str, top_k: int = 3):
    try:
        if config.USE_MOCK_VECTOR_STORE:
            from services.mock_vector_store import search_similar
        else:
            from services.vector_store import search_similar
        return search_similar(query, top_k=top_k)
    except Exception as e:
        logger.warning(f"[rag] Vector store retrieval error: {e}, falling back to mock vector store")
        from services.mock_vector_store import search_similar as fallback_search
        return fallback_search(query, top_k=top_k)


def _generate(query: str, context):
    try:
        if config.USE_MOCK_LLM:
            from services.mock_llm_service import generate_answer
        else:
            from services.llm_service import generate_answer
        return generate_answer(query, context)
    except Exception as e:
        logger.warning(f"[rag] LLM generation error: {e}, falling back to mock generator")
        from services.mock_llm_service import generate_answer as fallback_generate
        return fallback_generate(query, context)


def _rewrite_and_classify(query: str, history: List[dict]) -> dict:
    try:
        if config.USE_MOCK_LLM:
            from services.mock_llm_service import rewrite_and_classify
        else:
            from services.llm_service import rewrite_and_classify
        return rewrite_and_classify(query, history)
    except Exception as e:
        logger.warning(f"[rag] rewrite_and_classify error: {e}")
        return {"standalone_query": query, "intent": "service_question"}


def _generate_off_topic_response(query: str) -> str:
    try:
        if config.USE_MOCK_LLM:
            from services.mock_llm_service import generate_off_topic_response
        else:
            from services.llm_service import generate_off_topic_response
        return generate_off_topic_response(query)
    except Exception as e:
        logger.warning(f"[rag] off_topic generation error: {e}")
        from services.mock_llm_service import generate_off_topic_response as fallback_off_topic
        return fallback_off_topic(query)


def _count_answer() -> ChatResponse:
    """M-05: aggregate count questions are routed here instead of vector
    search, since retrieval only ever returns a top_k subset and can't count."""
    from services.pss_service import count_active_services

    try:
        counts = count_active_services()
        breakdown = ", ".join(
            f"{office}: {n}" for office, n in sorted(counts["per_office"].items())
        )
        answer = (
            f"PUP Caloocan's Citizen's Charter currently lists {counts['total']} active "
            f"services in total ({breakdown}). Ask me about a specific office or service "
            "and I can walk you through the requirements and steps."
        )
        return ChatResponse(answer=answer, confidence=1.0, escalated=False)
    except Exception:  
        return ChatResponse(answer=NO_CONTEXT_MESSAGE, escalated=True)


def _office_services_answer(office: str) -> ChatResponse:
    """M-05 (extended): per-office "what/how many services does X have"
    questions routed here instead of vector search - there's no single
    text_chunk that lists "all services of an office", so retrieval always
    surfaced a weak, unrelated top match for these questions (e.g. "ilan ang
    services ng Academic office?" was matching "Consultation Service" at
    54%). fetch_active_services() already normalizes each row's office into
    the same 3-category taxonomy detect_office_query() returns, so a plain
    equality filter is enough - no fuzzy matching needed here.
    """
    from services.pss_service import fetch_active_services

    try:
        all_services = fetch_active_services()
        matched = [s for s in all_services if s.get("office") == office]

        if not matched:
            return ChatResponse(answer=NO_CONTEXT_MESSAGE, escalated=True)

        names = "; ".join(s["name"] for s in matched)
        answer = (
            f"The {office} Office currently has {len(matched)} active service"
            f"{'s' if len(matched) != 1 else ''} in the Citizen's Charter: {names}. "
            "Ask me about any specific one and I can walk you through its "
            "requirements, steps, and processing time."
        )
        return ChatResponse(answer=answer, confidence=1.0, escalated=False)
    except Exception:  
        return ChatResponse(answer=NO_CONTEXT_MESSAGE, escalated=True)


def align_matches_with_answer(answer: str, results: List[dict]) -> tuple[Optional[dict], List[dict]]:
    """Align retrieved vector results with the LLM's actual generated answer.

    If the LLM answered about results[1] or results[2] instead of results[0],
    surface the actual discussed service as the top matched service.
    """
    if not results:
        return None, []

    ans_lower = answer.lower()
    scored_results = []

    for r in results:
        name = (r.get("service_name") or r.get("name") or "").lower()
        sim = float(r.get("similarity", 0.0))

        cleaned_name = (
            name.replace("processing of application for", "")
            .replace("processing of request for", "")
            .replace("processing of", "")
            .replace("application for", "")
            .replace("request for", "")
            .replace("issuance of", "")
            .strip()
        )
        words = [w for w in cleaned_name.split() if len(w) > 2]

        if not words:
            words = [w for w in name.split() if len(w) > 2]

        matches = sum(1 for w in words if w in ans_lower)
        match_ratio = matches / len(words) if words else 0.0

        phrase_match = 1.0 if cleaned_name and cleaned_name in ans_lower else 0.0

        alignment_score = (phrase_match * 0.5) + (match_ratio * 0.3) + (sim * 0.2)
        scored_results.append((alignment_score, r))

    scored_results.sort(key=lambda x: x[0], reverse=True)

    best_score, top = scored_results[0]
    if best_score < 0.2:
        top = results[0]

    valid_results = [r for r in results if float(r.get("similarity", 0.0)) >= 0.40]

    if top in valid_results:
        valid_results.remove(top)
        valid_results.insert(0, top)

    return top, valid_results


class RAGOrchestrator:
    def process_query(
        self,
        query: str,
        session_id: str,
        chat_history: Optional[List[dict]] = None,
    ) -> ChatResponse:
        start = time.time()
        chat_history = chat_history or []

        query = (query or "").strip()
        if not query:
            raise ValueError("Query cannot be empty")
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]

        try:
            office = detect_office_query(query)
            if office:
                return self._finalize(
                    _office_services_answer(office), session_id, query, start
                )

            if is_aggregate_count_query(query):
                return self._finalize(_count_answer(), session_id, query, start)

            recent_history = chat_history[-HISTORY_TURNS_FOR_REWRITE:]
            rewritten = _rewrite_and_classify(query, recent_history)

            if rewritten["intent"] == "off_topic":
                off_topic_ans = _generate_off_topic_response(query)
                return self._finalize(
                    ChatResponse(answer=off_topic_ans, escalated=False),
                    session_id, query, start,
                )

            standalone_query = rewritten["standalone_query"]

            office = detect_office_query(standalone_query)
            if office:
                return self._finalize(
                    _office_services_answer(office), session_id, query, start
                )

            if is_aggregate_count_query(standalone_query):
                return self._finalize(_count_answer(), session_id, query, start)

            search_query = expand_query(standalone_query)

            results = _search(search_query, top_k=3)

            if results:
                logger.info(
                    "[rag] query=%r -> top matches: %s",
                    search_query,
                    ", ".join(
                        f"{r.get('service_name')!r} (confidence={r.get('similarity', 0):.2f})"
                        for r in results
                    ),
                )
            else:
                logger.info("[rag] query=%r -> no matches above threshold", search_query)

            if not results:
                return self._finalize(
                    ChatResponse(answer=NO_CONTEXT_MESSAGE, escalated=True),
                    session_id, query, start,
                )

            answer = _generate(search_query, results)

            is_refusal = (
                "i do not have specific information" in answer.lower()
                or "i don't have specific information" in answer.lower()
                or "please visit the concerned office" in answer.lower()
                or "i can only show a few services" in answer.lower()
            )
            if is_refusal or not check_response_uses_context(answer, results):
                return self._finalize(
                    ChatResponse(answer=NO_CONTEXT_MESSAGE, escalated=True),
                    session_id, query, start,
                )

            top, aligned_results = align_matches_with_answer(answer, results)
            if not top:
                top = results[0]

            confidence = float(top.get("similarity", 0.0))

            matched_services = [
                MatchedService(
                    service_id=str(r.get("service_id", "")),
                    service_name=r.get("service_name"),
                    office=r.get("office"),
                    confidence=round(float(r.get("similarity", 0.0)), 4),
                )
                for r in aligned_results
            ]

            has_valid_top = confidence >= 0.40

            escalated = (
                confidence < ESCALATION_CONFIDENCE_THRESHOLD
                or "please visit" in answer.lower()
            )

            return self._finalize(
                ChatResponse(
                    answer=answer,
                    matched_service=top.get("service_name") if has_valid_top else None,
                    matched_service_id=str(top.get("service_id", "")) if has_valid_top else None,
                    office=top.get("office") if has_valid_top else None,
                    confidence=round(confidence, 4),
                    matched_services=matched_services,
                    escalated=escalated,
                ),
                session_id,
                query,
                start,
            )

        except TimeoutError:
            return self._finalize(
                ChatResponse(answer=TIMEOUT_MESSAGE, escalated=True),
                session_id, query, start,
            )
        except Exception as e:
            logger.exception(f"[rag] process_query unexpected error: {e}")
            return self._finalize(
                ChatResponse(
                    answer=NO_CONTEXT_MESSAGE,
                    escalated=True,
                ),
                session_id,
                query,
                start,
            )

    def _finalize(
        self, response: ChatResponse, session_id: str, query: str, start: float
    ) -> ChatResponse:
        elapsed = time.time() - start
        if elapsed > PIPELINE_TIMEOUT_SECONDS:
            response = ChatResponse(answer=TIMEOUT_MESSAGE, escalated=True)

        response.response_time_ms = int(elapsed * 1000)
        self._log_async(session_id, query, response)
        return response

    def _log_async(self, session_id: str, query: str, r: ChatResponse) -> None:
        coro = logging_service.log_interaction(
            session_id=session_id,
            query_text=query,
            matched_service_id=r.matched_service_id or "",
            matched_service_name=r.matched_service or "",
            office=r.office or "",
            confidence=r.confidence,
            response_time_ms=r.response_time_ms,
            escalated=r.escalated,
        )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)  
        except RuntimeError:
            try:
                asyncio.run(coro)  
            except Exception:  
                import logging as _logging
                _logging.getLogger(__name__).exception(
                    "log_interaction failed (non-fatal, response already sent)"
                )