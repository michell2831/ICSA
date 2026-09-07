"""AI-04 mock: canned response in <100ms with ZERO Groq API calls.

Enabled via USE_MOCK_LLM=true. Used in Week 1 dev and in all unit tests.
"""
from typing import List

from utils.query_preprocessing import expand_query, is_obviously_casual


def rewrite_and_classify(query: str, history: List[dict]) -> dict:
    """Deterministic mock of the real LLM rewrite/classify call — no network,
    so offline dev (USE_MOCK_LLM=true) and unit tests stay fast and stable.

    Doesn't do real pronoun resolution (that needs an LLM), just the
    dictionary-based acronym/Taglish expansion plus a keyword off-topic check,
    which is enough to exercise the H-01/H-02/M-04 pipeline branches in tests.
    """
    intent = "off_topic" if is_obviously_casual(query) else "service_question"
    return {"standalone_query": expand_query(query), "intent": intent}


def generate_off_topic_response(query: str) -> str:
    q = (query or "").strip().lower()
    if any(w in q for w in ["wala", "no", "none", "nothing", "bye", "salamat", "thank you", "thanks", "nvm"]):
        return (
            "Alright! Have a great day ahead. Feel free to return anytime if you have "
            "any questions about PUP Caloocan campus services!"
        )
    if any(w in q for w in ["chicken", "manok", "food", "pagkain"]):
        return (
            "I can only assist with official PUP Caloocan campus services. "
            "Food requests like chicken are not covered under the Citizen's Charter, "
            "but I can help you with student IDs, enrollment, or health services!"
        )
    return (
        "I'm here to assist with official PUP Caloocan Citizen's Charter services "
        "(such as enrollment, student IDs, or medical certificates). "
        "Please feel free to ask about any campus service!"
    )


def generate_answer(query: str, context_services: List[dict]) -> str:
    if not context_services:
        return (
            "I do not have specific information about that service. "
            "Please visit the concerned office directly."
        )
    top = context_services[0]
    name = top.get("service_name") or top.get("name", "the requested service")
    office = top.get("office", "the concerned office")
    sla = f"{top.get('sla_target_value', '')} {top.get('sla_target_unit', '')}".strip()
    return (
        f"Based on PUP Caloocan Citizen's Charter, the service that matches "
        f"your question is **\"{name}\"** handled by the **{office}** office.\n\n"
        f"• **Processing Time (SLA):** {sla or 'Standard processing'}\n"
        f"• **Instructions:** Please prepare the required documents and proceed to {office} during campus working hours (Mon-Fri, 8:00 AM - 5:00 PM)."
    )