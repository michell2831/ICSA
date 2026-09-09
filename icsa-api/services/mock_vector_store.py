"""AI-03 mock: keyword-overlap "fake similarity" search — NO real database.

Enabled via USE_MOCK_VECTOR_STORE=true — lets FE/AI develop offline.

IMPORTANT (fix, was: always returned the same 3 fixed results regardless of
query, which made it impossible to test H-02 acronym/Taglish expansion or
H-01 query rewriting offline — every query "matched" Medical Certificate at
0.87 no matter what). This version scores each fixture by word overlap
against the query, so different queries surface different top matches,
close enough to real vector search behavior for local/offline testing.
"""
from typing import List

_MOCK_SERVICES = [
    {
        "service_id": "6d0a3f9e-mock-0001",
        "service_name": "Consultation and Treatment Services for Non-Emergency Medical Cases (Issuance of Medical Certificate)",
        "office": "Administrative",
        "text_chunk": (
            "Service: Consultation and Treatment Services for Non-Emergency Medical Cases. "
            "Office: Administrative. Requirements: Accomplished Patient Information Sheet, "
            "valid PUP ID. Steps: Register at the Medical Clinic; Undergo consultation with "
            "the campus physician; Receive prescribed treatment or medical certificate. "
            "Output: Medical certificate issued."
        ),
        "sla_target_value": 30,
        "sla_target_unit": "Minutes",
    },
    {
        "service_id": "6d0a3f9e-mock-0002",
        "service_name": "Application for New Identification Card",
        "office": "OSAS",
        "text_chunk": (
            "Service: Application for New Identification Card. Office: OSAS. "
            "Requirements: Registration Certificate, ID application form. "
            "Steps: Submit accomplished form; Photo capture; Claim ID on release date. "
            "Output: New student ID issued."
        ),
        "sla_target_value": 15,
        "sla_target_unit": "Minutes",
    },
    {
        "service_id": "6d0a3f9e-mock-0003",
        "service_name": "Processing of Application for Cross-Enrollment",
        "office": "Academic",
        "text_chunk": (
            "Service: Processing of Application for Cross-Enrollment. Office: Academic. "
            "Requirements: Application Letter for Cross-Enrollment, Permit to Cross-Enroll. "
            "Steps: Evaluate letter; Approve or deny request; Issue permit to cross-enroll. "
            "Output: Permit to cross-enroll issued."
        ),
        "sla_target_value": 10,
        "sla_target_unit": "Minutes",
    },
    {
        "service_id": "6d0a3f9e-mock-0004",
        "service_name": "Issuance of Certificate of Registration (COR)",
        "office": "Academic",
        "text_chunk": (
            "Service: Issuance of Certificate of Registration. Office: Academic. "
            "Requirements: Validated enrollment form, valid PUP ID. "
            "Steps: Log in to the student portal; Confirm enrolled subjects; "
            "Download or print the Certificate of Registration. "
            "Output: Certificate of Registration (COR) issued."
        ),
        "sla_target_value": 20,
        "sla_target_unit": "Minutes",
    },
    {
        "service_id": "6d0a3f9e-mock-0005",
        "service_name": "Application for Leave of Absence (LOA)",
        "office": "Academic",
        "text_chunk": (
            "Service: Application for Leave of Absence. Office: Academic. "
            "Requirements: Leave of Absence form, letter of intent, valid PUP ID. "
            "Steps: Submit LOA form to the Registrar; Wait for approval; "
            "Receive approved Leave of Absence document. "
            "Output: Approved Leave of Absence."
        ),
        "sla_target_value": 3,
        "sla_target_unit": "Days",
    },
    {
        "service_id": "6d0a3f9e-mock-0006",
        "service_name": "Request for Transcript of Records (TOR)",
        "office": "Academic",
        "text_chunk": (
            "Service: Request for Transcript of Records. Office: Academic. "
            "Requirements: Clearance form, valid PUP ID, request slip. "
            "Steps: File request at the Registrar; Pay corresponding fee; "
            "Claim Transcript of Records on release date. "
            "Output: Transcript of Records (TOR) released."
        ),
        "sla_target_value": 5,
        "sla_target_unit": "Days",
    },
    {
        "service_id": "9fbe082f-980a-4408-a656-47a8227a96d8",
        "service_name": "Request for Certificate of Good Moral Character",
        "office": "OSAS",
        "text_chunk": (
            "Service: Request for Certificate of Good Moral Character (Issuance of Good Moral Certificate). "
            "Office: OSAS (Office of Student Services). "
            "Requirements: Accomplished Request Form, valid PUP Student Identification Card (ID), "
            "Authorization Letter and valid ID of claimant if representative. "
            "Steps: Submit accomplished request form to the OSAS receiving area; "
            "Staff logs request and issues claim stub; "
            "Process and prepare the Certificate of Good Moral Character; "
            "Issue Certificate of Good Moral Character; Client signs in logbook. "
            "Output: Certificate of Good Moral Character issued."
        ),
        "sla_target_value": 37,
        "sla_target_unit": "Minutes",
    },
]

SIMILARITY_THRESHOLD = 0.30

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "is", "are",
    "what", "how", "do", "i", "you", "your", "my", "please", "with", "at",
    "ang", "ng", "sa", "para", "ano", "paano", "po", "ba", "mga", "na", "ay",
    "get", "how to",
}


def _tokenize(text: str) -> set:
    words = [w.strip(".,:;()!?\"'") for w in text.lower().split()]
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _fake_similarity(query_tokens: set, text_chunk: str) -> float:
    """Jaccard-style overlap between query tokens and the service text_chunk.

    Not a real embedding similarity — just enough signal so different mock
    queries surface different top matches during offline testing.
    """
    chunk_tokens = _tokenize(text_chunk)
    if not query_tokens or not chunk_tokens:
        return 0.0
    overlap = query_tokens & chunk_tokens
    if not overlap:
        return 0.0
    # Weight toward how much of the (short) query matched, since queries are
    # much shorter than the text_chunk they're being compared against.
    return round(len(overlap) / len(query_tokens), 4)


def store_embeddings(services: List[dict]) -> None:  # pragma: no cover
    return None  # no-op in mock mode


def search_similar(query_text: str, top_k: int = 3) -> List[dict]:
    """Score each mock service by keyword overlap with the query, apply the
    same 0.30 threshold guard as the real vector_store.py, and return the
    top_k results sorted by (fake) similarity."""
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return []

    scored = []
    for svc in _MOCK_SERVICES:
        sim = _fake_similarity(query_tokens, svc["text_chunk"])
        if sim > 0:
            scored.append({**svc, "similarity": sim})

    scored.sort(key=lambda r: r["similarity"], reverse=True)

    if not scored or scored[0]["similarity"] < SIMILARITY_THRESHOLD:
        return []  # below threshold — no-context response, never hallucinate

    return [r for r in scored if r["similarity"] >= SIMILARITY_THRESHOLD][:top_k]