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
        from groq import Groq
        _client = Groq(api_key=config.get_groq_api_key())
    return _client


def generate_off_topic_response(query: str) -> str:
    """Generate a friendly, dynamic refusal/redirect for off-topic/casual queries via Groq."""
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=config.GROQ_MODEL,
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
    except Exception:
        pass
    return (
        "I can only assist with official PUP Caloocan campus services (such as enrollment, "
        "student IDs, medical certificates, or academic requests). Please let me know if you "
        "have a question about a campus service!"
    )


def generate_answer(query: str, context_services: List[dict]) -> str:
    """Generate a grounded plain-language answer via Groq.

    Retries once (after 2s) on rate-limit/connection errors, then raises
    TimeoutError so the orchestrator can return the fixed timeout message.
    """
    from groq import APIConnectionError, APITimeoutError, RateLimitError

    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(query, context_services)},
    ]

    last_err = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                max_tokens=config.GROQ_MAX_TOKENS,
                temperature=0.1,
                timeout=config.GROQ_TIMEOUT_SECONDS,
            )
            return resp.choices[0].message.content or ""
        except (RateLimitError, APIConnectionError, APITimeoutError) as e:
            last_err = e
            if attempt == 0:
                time.sleep(2)

    raise TimeoutError(f"Groq unavailable after retry: {last_err}")


def rewrite_and_classify(query: str, history: List[dict]) -> dict:
    """H-01/H-02/M-04: one cheap Groq call that rewrites follow-ups into a
    standalone search query (using chat history), expands acronyms/Taglish,
    and classifies whether the turn is even a service question.

    Fails soft: any error, timeout, or malformed JSON just falls back to
    treating the raw query as already-standalone and service-related, so a
    hiccup in this step never blocks the rest of the pipeline.
    """
    fallback = {"standalone_query": query, "intent": "service_question"}
    if not history:
        pass

    from groq import APIConnectionError, APITimeoutError, RateLimitError

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=config.GROQ_MODEL,
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
    except (RateLimitError, APIConnectionError, APITimeoutError, TimeoutError):
        return fallback
    except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError):
        return fallback