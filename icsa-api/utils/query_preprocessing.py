"""AI Specialist fixes — H-02 (acronym/Taglish expansion), M-05 (aggregate
count + per-office listing) fast-path deterministic detection used ahead of
the LLM rewrite/classify step, and M-04 off-topic pre-filtering.

Kept deterministic and dictionary-based on purpose: acronym expansion and
"is this obviously a count/listing question" detection don't need an LLM
round trip, so we handle the high-confidence cases here for free and only
fall back to the LLM (services.llm_service.rewrite_and_classify) for
anything ambiguous.
"""
import re
from typing import List, Optional


ACRONYM_EXPANSIONS = {
    "COR": "Certificate of Registration",
    "LOA": "Leave of Absence",
    "ODRS": "Online Document Request System",
    "TOR": "Transcript of Records",
    "GWA": "General Weighted Average",
    "CAV": "Certification, Authentication and Verification",
    "OSAS": "Office of Student Services",
    "PSS": "PUP Service Standard",
}

TAGLISH_PHRASE_MAP = [
    ("paano kumuha ng", "how to get"),
    ("paano mag apply ng", "how to apply for"),
    ("paano mag-apply ng", "how to apply for"),
    ("paano mag file ng", "how to file"),
    ("paano mag-file ng", "how to file"),
    ("saan ako kukuha ng", "where do I get"),
    ("ilang araw bago", "how many days before"),
    ("magkano ang", "how much is the"),
]

_ACRONYM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in ACRONYM_EXPANSIONS) + r")\b",
    re.IGNORECASE,
)


def expand_query(text: str) -> str:
    """Deterministically expand known Taglish phrases and acronyms.

    Returns the original text with expansions appended (not replaced) so the
    embedding model sees both the literal user phrasing and its English
    expansion, maximizing the chance of a vector-search hit either way.
    """
    if not text:
        return text

    lowered = text.lower()
    expansions: List[str] = []

    for phrase, english in TAGLISH_PHRASE_MAP:
        if phrase in lowered:
            expansions.append(english)

    def _replace(match: "re.Match") -> str:
        found = match.group(0).upper()
        expansions.append(ACRONYM_EXPANSIONS.get(found, found))
        return match.group(0)

    _ACRONYM_PATTERN.sub(_replace, text)

    if not expansions:
        return text
    return f"{text} ({'; '.join(expansions)})"


_COUNT_PATTERNS = [
    re.compile(r"\bhow many (total )?services\b", re.IGNORECASE),
    re.compile(r"\btotal (number of )?services\b", re.IGNORECASE),
    re.compile(r"\bilang (lahat ng )?serbisyo\b", re.IGNORECASE),
    re.compile(r"\bkabuuang (bilang ng )?serbisyo\b", re.IGNORECASE),
    re.compile(r"\ball (of )?(the )?services (are there|do you have|available)\b", re.IGNORECASE),
]


def is_aggregate_count_query(text: str) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in _COUNT_PATTERNS)


_SERVICE_WORD_PATTERN = re.compile(r"\b(services?|serbisyo)\b", re.IGNORECASE)

_OFFICE_KEYWORDS = {
    "Academic": ["academic", "akademiko"],
    "Administrative": ["administrative", "admin office", "administratibo"],
    "OSAS": ["osas", "student services", "student affairs", "student services and affairs"],
}


def detect_office_query(text: str) -> Optional[str]:
    """Returns the normalized office name ("Academic"/"Administrative"/
    "OSAS") if the query is asking about that office's services, else None.

    Deliberately narrow: only fires when the query mentions BOTH a
    "services" word AND a recognizable office name, so it doesn't
    accidentally swallow normal single-service questions (e.g. "what are
    the requirements for LOA" doesn't mention an office name, so this
    returns None and the query proceeds through normal vector search).
    """
    if not text or not _SERVICE_WORD_PATTERN.search(text):
        return None

    lowered = text.lower()
    for office, keywords in _OFFICE_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return office
    return None


_CASUAL_PATTERNS = [
    re.compile(r"^(hi|hello|hey|kumusta|kamusta|wala|no|none|nothing|oki|ok|okay|sige|cge|ahw|aw|bye|nvm|salamat|thanks|thank you)[!.\s]*$", re.IGNORECASE),
    re.compile(r"\b(huhu+|haha+|lol|miss ko na|i love you|ily)\b", re.IGNORECASE),
    re.compile(r"^(thank you|thanks|salamat|ok|okay|sige|cge)[!.\s]*$", re.IGNORECASE),
]


def is_obviously_casual(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    return any(p.search(stripped) for p in _CASUAL_PATTERNS)