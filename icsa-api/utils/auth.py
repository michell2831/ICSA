"""ENH-01: PSS -> ICSA analytics access control.

The chatbot itself (Assistant tab, /api/chat) stays completely open - no
token needed, no role check. This module only guards /api/analytics/*.

Token format mirrors PSS exactly (see PSS src/services/auth.js):
    mock-token-<base64(JSON)>
    JSON = { userId, username, armsRole, office, isCrossOffice, displayName }

This is dev/mock-grade verification (no signature check) - matches how PSS
itself treats these tokens today (see auth.js top-of-file comment: "MOCK
TOKEN FORMAT"). If PSS moves to real signed JWTs, swap _decode_token() below
for real signature verification against PSS's public key/JWKS; everything
else here (the office-scoping logic) stays the same.
"""
import base64
import binascii
import json
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException

ANALYTICS_ALLOWED_ROLES = {"SUPER_ADMIN", "PLANNING_OFFICER", "SUBSYSTEM_ADMIN"}

_PSS_OFFICE_ALIAS = {
    "ACAD": "Academic",
    "ADMIN": "Administrative",
    "OSAS": "OSAS",
}


@dataclass
class ScopedUser:
    user_id: str
    username: str
    arms_role: str
    is_cross_office: bool
    office: Optional[str]


def _decode_token(token: str) -> dict:
    if not token.startswith("mock-token-"):
        raise HTTPException(status_code=401, detail="Unsupported token format")
    b64_part = token[len("mock-token-"):]
    try:
        json_bytes = base64.b64decode(b64_part)
        return json.loads(json_bytes.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or malformed token")


def get_current_user(authorization: Optional[str] = Header(None)) -> ScopedUser:
    """FastAPI dependency - decodes the PSS token and returns a ScopedUser.
    Raises 401 if the token is missing, malformed, or unsupported."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization[len("Bearer "):].strip()
    claims = _decode_token(token)

    arms_role = claims.get("armsRole") or "STAFF"
    is_cross_office = bool(claims.get("isCrossOffice", False))
    pss_office = claims.get("office") or "ACAD"
    icsa_office = None if is_cross_office else _PSS_OFFICE_ALIAS.get(pss_office, pss_office)

    return ScopedUser(
        user_id=str(claims.get("userId") or claims.get("id") or "unknown"),
        username=claims.get("username") or "unknown",
        arms_role=arms_role,
        is_cross_office=is_cross_office,
        office=icsa_office,
    )


def require_analytics_access(user: ScopedUser = Depends(get_current_user)) -> ScopedUser:
    """FastAPI dependency - same as get_current_user(), but additionally
    rejects roles not allowed to view analytics at all (Staff, OPCR
    Evaluator)."""
    if user.arms_role not in ANALYTICS_ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to view analytics")
    return user


def resolve_scoped_office(requested_office: Optional[str], user: ScopedUser) -> Optional[str]:
    """The core enforcement point. Called at the top of every analytics
    endpoint with whatever `office` query param the client sent.

    Office-locked users (Office Heads): the client-requested office is
    IGNORED entirely - always their own office. This is what makes
    tampering the frontend dropdown/URL useless; even if a compromised or
    modified frontend sends ?office=Academic for an OSAS head, this
    function overrides it back to "OSAS".

    Cross-office users (Super Admin / Planning Officer): the requested
    filter is honored if present and valid; "ALL"/"All Offices"/empty means
    no filter (see everything).
    """
    if not user.is_cross_office:
        return user.office

    if not requested_office or requested_office in ("ALL", "All Offices", ""):
        return None
    return requested_office