"""AI-04: Groq / Llama 3.1 answer generation.

Terminology (do not confuse):
  Groq   = the inference API provider (console.groq.com)
  Llama  = the LLM family (Meta) hosted on Groq
  Ollama = optional LOCAL fallback only — not wired unless Groq is down

All config is read from .env via utils/config.py — nothing hardcoded.
"""
import json
import time
from typing import List

from utils import config
from utils.prompts import (
    OFF_TOPIC_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_rewrite_prompt,
    build_user_prompt,
)

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from groq import Groq
            api_key = config.get_groq_api_key()
            _client = Groq(api_key=api_key)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[llm_service] Could not initialize Groq client: {e}")
            return None
    return _client


def generate_off_topic_response(query: str) -> str:
    """Generate a friendly, dynamic refusal/redirect for off-topic/casual queries via Groq."""
    try:
        client = _get_client()
        if client is not None:
            model_name = config.GROQ_MODEL
            if "/" in model_name or "compound" in model_name or not model_name:
                model_name = "llama-3.1-8b-instant"

            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": OFF_TOPIC_SYSTEM_PROMPT},
                    {"role": "user", "content": f"CITIZEN MESSAGE: {query}"},
                ],
                max_tokens=150,
                temperature=0.3,
                timeout=min(config.GROQ_TIMEOUT_SECONDS, 6),
            )
            answer = (resp.choices[0].message.content or "").strip()
            if answer:
                return answer
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[llm_service] off-topic generation error: {e}")

    from services.mock_llm_service import generate_off_topic_response as fallback_off_topic
    return fallback_off_topic(query)


def generate_answer(query: str, context_services: List[dict]) -> str:
    """Generate a grounded plain-language answer via Groq, with resilient fallback."""
    try:
        client = _get_client()
        if client is not None:
            model_name = config.GROQ_MODEL
            if "/" in model_name or "compound" in model_name or not model_name:
                model_name = "llama-3.1-8b-instant"

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(query, context_services)},
            ]

            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=config.GROQ_MAX_TOKENS,
                temperature=0.1,
                timeout=config.GROQ_TIMEOUT_SECONDS,
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return content
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[llm_service] Groq inference error: {e}, falling back to charter generator")

    from services.mock_llm_service import generate_answer as fallback_gen
    return fallback_gen(query, context_services)


def rewrite_and_classify(query: str, history: List[dict]) -> dict:
    """H-01/H-02/M-04: one cheap Groq call that rewrites follow-ups into a
    standalone search query (using chat history), expands acronyms/Taglish,
    and classifies whether the turn is even a service question.

    Fails soft: any error, timeout, or malformed JSON just falls back to
    treating the raw query as already-standalone and service-related, so a
    hiccup in this step never blocks the rest of the pipeline.
    """
    fallback = {"standalone_query": query, "intent": "service_question"}

    try:
        client = _get_client()
        if client is not None:
            model_name = config.GROQ_MODEL
            if "/" in model_name or "compound" in model_name or not model_name:
                model_name = "llama-3.1-8b-instant"

            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": build_rewrite_prompt(query, history)},
                ],
                max_tokens=200,
                temperature=0.0,
                timeout=min(config.GROQ_TIMEOUT_SECONDS, 6),
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or ""
            parsed = json.loads(raw)
            standalone_query = (parsed.get("standalone_query") or query).strip() or query
            intent = parsed.get("intent") if parsed.get("intent") in (
                "service_question", "off_topic"
            ) else "service_question"
            return {"standalone_query": standalone_query, "intent": intent}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[llm_service] rewrite_and_classify error: {e}")
        return fallback

    return fallback