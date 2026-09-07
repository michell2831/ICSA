"""AI-07: System prompt + hallucination safeguards for the ICSA chatbot."""
from typing import List

SYSTEM_PROMPT = """You are the official citizen service assistant for PUP Caloocan Campus.
Always respond in clear, simple English, regardless of what language the citizen wrote in. You must fully understand Filipino, Taglish, and PUP Caloocan-specific acronyms in the citizen's question, but your reply itself should be in English.
Answer ONLY using the service information provided below. Do not invent steps, requirements, document names, or SLA values.
Format: List requirements as bullet points. If a service lists "Requirements: None listed", state clearly and politely that no specific prior documents are required, and briefly outline the steps to complete the service. List steps as a numbered list. Always include the SLA exactly as given to you in the context (it is already in human-readable form, e.g. "1 working day, 2 hours") -- never convert it back into raw minutes.
If the provided context is completely unrelated to the citizen's question or missing, respond: I do not have specific information about that service. Please visit the concerned office directly.
You only ever see up to 3 retrieved services, never the full catalogue. Never state or imply an exact total count of services (e.g. "there are 2 services under X office"). If asked how many services exist, say you can only show a few at a time and invite the user to ask about a specific office or service instead.
Never ask for, collect, or repeat personal information from the user.
Fee and payment questions: If the citizen asks whether a fee is required and the service steps mention paying at a cashier, counter, or payment office, confirm that a processing fee applies and advise the citizen to confirm the exact amount at the respective office or cashier upon processing. Do not say you have no information about fees if payment is clearly part of the service steps.
If the citizen specifically asks for the exact peso amount and it is not given in the context, never phrase it as "I do not have specific information" or "I don't have specific information" -- instead say something like: "The exact fee amount isn't listed in our records, but you can confirm it directly at the Cashier's Office when you process your request." Keep the answer grounded in what you do know (that a fee applies, and where to confirm it) even when the exact peso amount isn't available.
Narrow-scope answers: If the citizen's question is specifically and only about processing time or SLA, answer with only the SLA. If specifically about requirements and no prior documents are listed in the charter, state politely that no specific prior documents are required for this service. Match the scope of your answer to the scope of the question."""

# Rough safety margin: ~4 chars per token → 2000 tokens ≈ 8000 chars
_MAX_PROMPT_CHARS = 8000

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "is", "are",
    "what", "how", "do", "i", "you", "your", "my", "please", "with", "at",
    "ang", "ng", "sa", "para", "ano", "paano", "po", "ba", "mga", "na", "ay",
}


def _format_service(svc: dict) -> str:
    from services.pss_service import humanize_sla

    sla = humanize_sla(svc.get("sla_target_value"), svc.get("sla_target_unit"))
    return (
        f"Service: {svc.get('service_name') or svc.get('name', '')}\n"
        f"Office: {svc.get('office', '')}\n"
        f"SLA: {sla}\n"
        f"Details: {svc.get('text_chunk', '')}"
    )


# ---------------------------------------------------------------------------
# H-01 / H-02 / M-04: single combined "understand the turn" step, run BEFORE
# vector search. One LLM call does three jobs at once instead of three:
#   1. Rewrite follow-up questions ("yes that", "what about the requirements?")
#      into a standalone, self-contained search query using recent history.
#   2. Expand PUP acronyms / Taglish phrasing into English search terms
#      (synergistic with the deterministic dictionary in query_preprocessing.py —
#      this catches acronyms/slang NOT in that fixed dictionary).
#   3. Classify whether the turn is even a service question at all, so
#      obviously casual/off-topic chat ("miss ko na sya huhu") never gets
#      routed through vector search + the rigid no-context fallback.
# ---------------------------------------------------------------------------
REWRITE_SYSTEM_PROMPT = """You are a query-understanding step for a PUP Caloocan citizen service chatbot.
The citizen may write in English, Filipino, or Taglish — you must understand all of these, but your output must always be in English.
Given the recent conversation and the citizen's latest message, output ONLY a JSON object (no markdown, no commentary) with exactly these keys:
{"standalone_query": "...", "intent": "service_question" | "off_topic"}

Rules for standalone_query:
- Rewrite the latest message into a fully self-contained ENGLISH search query, resolving pronouns and references using the conversation history (e.g. "what are the requirements for that?" after discussing Medical Certificate -> "What are the requirements for a Medical Certificate?").
- Translate Filipino/Taglish phrasing into plain English, and expand any PUP/university acronyms into English search terms.
- If the message is already self-contained English, only clean it up minimally.

Rules for intent:
- "off_topic" if the message is casual conversation, greetings, small talk, venting, or otherwise unrelated to a PUP Caloocan citizen service (documents, requirements, steps, SLA, offices).
- "service_question" for anything about a specific service, requirements, steps, SLA, or office -- including short follow-ups to an ongoing service discussion.

Watch for ambiguous Filipino words that have both a personal/emotional meaning and an unrelated literal meaning -- judge from the FULL message and conversation context, not the word alone:
- "mahal" can mean "expensive" (fees/pricing) OR "love" (as in "mahal kita", "mahal pa ba niya ko" -- romantic/relationship questions). A question about whether someone still loves the citizen is "off_topic", never a pricing question.
- When a message reads as personal, romantic, or relationship-related, classify it "off_topic" even if it contains a word that also has a pricing/fee meaning in another context.
"""

OFF_TOPIC_SYSTEM_PROMPT = """You are the official citizen service assistant for PUP Caloocan Campus.
The citizen sent a message that is casual, off-topic, or conversational.

Respond in 1-2 friendly, polite sentences in English according to their intent:
1. If the citizen is saying 'no', 'wala', 'none', 'nothing', 'bye', 'salamat', 'thank you', or ending the chat:
   Acknowledge warmly and conclude (e.g. "Alright! Have a great day ahead. Feel free to return anytime if you need help with PUP Caloocan services!"). DO NOT push or repeatedly ask them what service they want when they already declined.
2. If the citizen is asking about non-university topics (e.g. food requests like 'chicken', weather, personal topics):
   Politely explain that you can only assist with official PUP Caloocan campus services (such as enrollment, student ID, medical certificates, or academic requests).
3. If the citizen is making small talk ('cge', 'okay', 'hi'):
   Acknowledge naturally and warmly."""


def build_rewrite_prompt(query: str, history: List[dict]) -> str:
    """Formats recent turns (last 3-5) + the new message for the rewrite/classify call."""
    lines = []
    for turn in history[-5:]:
        role = "Citizen" if turn.get("role") == "citizen" else "Assistant"
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    history_block = "\n".join(lines) if lines else "(no prior turns)"
    return (
        f"CONVERSATION SO FAR:\n{history_block}\n\n"
        f"LATEST CITIZEN MESSAGE: {query}\n\n"
        "Output the JSON object now."
    )


def build_user_prompt(query: str, context_services: List[dict]) -> str:
    """Formats the retrieved context block + citizen question into one prompt.

    Context is placed BEFORE the question (better grounding), and the total
    output is capped at ~2000 tokens.
    """
    blocks = []
    budget = _MAX_PROMPT_CHARS - len(query) - 200
    for svc in context_services:
        block = _format_service(svc)
        if budget - len(block) < 0:
            break
        blocks.append(block)
        budget -= len(block)

    context = "\n\n---\n\n".join(blocks)
    return (
        "OFFICIAL SERVICE INFORMATION (answer ONLY from this):\n"
        f"{context}\n\n"
        f"CITIZEN QUESTION: {query}"
    )


def check_response_uses_context(response: str, context: List[dict]) -> bool:
    """Keyword-overlap hallucination guard.

    Returns False when the response shares no meaningful terms with the
    retrieved context -- i.e., the answer is likely off-topic/hallucinated.
    """
    if not response or not context:
        return False

    context_text = " ".join(_format_service(s) for s in context).lower()
    context_terms = {
        w.strip(".,:;()!?") for w in context_text.split()
        if len(w) > 3 and w not in _STOPWORDS
    }
    response_terms = {
        w.strip(".,:;()!?") for w in response.lower().split()
        if len(w) > 3 and w not in _STOPWORDS
    }
    return len(context_terms & response_terms) > 0