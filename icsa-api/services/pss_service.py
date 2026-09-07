"""PSS live data access — READ-ONLY (No-Touch rule).

This is the single module allowed to talk to the PSS PostgreSQL database.
It only ever runs SELECT through the readonly_icsa role. Zero writes, ever.

Used by:
  - GET  /api/services          (routers/services.py — live service catalogue)
  - POST /api/admin/reindex     (ETL extract + embed, on demand)
  - scripts/etl/extract_services.py (nightly cron path)
"""
from typing import List, Optional

import psycopg2
import psycopg2.extras

from utils import config
from utils.config import ConfigError

COLUMNS = [
    "id", "name", "office", "classification", "sla_target_value",
    "sla_target_unit", "processing_steps", "required_documents", "expected_output",
]

_BASE_SELECT = f"SELECT {', '.join(COLUMNS)} FROM service WHERE status = 'Active'"

_OFFICE_MAP = {
    "campus academic office": "Academic",
    "campus administrative office": "Administrative",
    "office of student services": "OSAS",
    "campus student services and affairs office": "OSAS",
    "acad": "Academic",
    "admin": "Administrative",
}

_SERVICE_NAME_MAP = {
    "Processing of Application for Correction of Grade Entry, Late Reporting of Grades and Removal of In…": (
        "Processing of Application for Correction of Grade Entry, Late Reporting of Grades and Removal of Incomplete Grade"
    ),
    "Processing of Request for Correction of Entry of Grade, Completion of Incomplete Grade, Late Report…": (
        "Processing of Request for Correction of Entry of Grade, Completion of Incomplete Grade, Late Reporting of Grades"
    ),
    "Processing of Request for Correction of Name in Conformity with the Philippines Statistics Authorit…": (
        "Processing of Request for Correction of Name in Conformity with Philippine Statistics Authority (PSA) Certificate of Live Birth"
    ),
    "Processing of Request for Correction of Name in Conformity with PSA Certificate of Live Birth and/o…": (
        "Processing of Request for Correction of Name in Conformity with PSA Certificate of Live Birth and/or Marriage"
    ),
    "Consultation and Treatment Services for Emergency Dental Cases of Faculty and Administrative Employ…": (
        "Consultation and Treatment Services for Emergency Dental Cases of Faculty and Administrative Employees"
    ),
    "Consultation and Treatment Services for Emergency Medical Cases of Faculty and Administrative Emplo…": (
        "Consultation and Treatment Services for Emergency Medical Cases of Faculty and Administrative Employees"
    ),
    "Consultation and Treatment Services for Non-Emergency Medical Cases of Faculty and Administrative E…": (
        "Consultation and Treatment Services for Non-Emergency Medical Cases of Faculty and Administrative Employees"
    ),
    "Consultation and Treatment Services for Non-Emergency Dental Cases of Faculty and Administrative Em…": (
        "Consultation and Treatment Services for Non-Emergency Dental Cases of Faculty and Administrative Employees"
    ),
}


def normalize_service_name(raw_name: Optional[str]) -> Optional[str]:
    """Restore full, untruncated service names for rows truncated in PSS DB."""
    if not raw_name:
        return raw_name
    cleaned = raw_name.strip()
    return _SERVICE_NAME_MAP.get(cleaned, cleaned)


def normalize_office(raw_office: Optional[str]) -> str:
    """Map a real PSS office string to ICSA's simplified 3-category taxonomy.

    Unknown/unmapped values are returned unchanged (not silently dropped),
    so a new or renamed PSS office shows up visibly in the dashboard/logs
    as its raw name instead of disappearing or crashing.
    """
    if not raw_office:
        return raw_office
    key = raw_office.strip().lower()
    return _OFFICE_MAP.get(key, raw_office)


def _connect():
    url = (config.PSS_DB_URL or "").strip()
    if not url:
        raise ConfigError(
            "PSS_DB_URL not set in .env — ask the PSS BE developer for the "
            "read-only (SELECT-only) credential (DE-01)."
        )
    return psycopg2.connect(url)


def fetch_active_services(
    office: Optional[str] = None, limit: Optional[int] = None
) -> List[dict]:
    """SELECT active services live from PSS. Parameterized — no injection."""
    sql = _BASE_SELECT
    params: list = []
    if office:
        sql += " AND office ILIKE %s"
        params.append(f"%{office}%")
    sql += " ORDER BY office, name"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)

    with _connect() as conn, conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]

    for r in rows:
        r["id"] = str(r["id"])
        r["name"] = normalize_service_name(r.get("name"))
        r["processing_steps"] = r.get("processing_steps") or []
        r["required_documents"] = r.get("required_documents") or []
        r["office"] = normalize_office(r.get("office"))
    return rows


def count_active_services() -> dict:
    """Total + per-office counts (used by DE-08 data validation)."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT office, COUNT(*) FROM service WHERE status = 'Active' "
            "GROUP BY office ORDER BY office"
        )
        raw_counts = cur.fetchall()

    per_office: dict = {}
    for raw_name, count in raw_counts:
        normalized = normalize_office(raw_name)
        per_office[normalized] = per_office.get(normalized, 0) + int(count)

    return {"total": sum(per_office.values()), "per_office": per_office}


_WORKING_DAY_MINUTES = 8 * 60


def humanize_sla(value, unit: Optional[str]) -> str:
    """Convert a raw SLA value into a citizen-readable duration string.

    Falls back to the raw "{value} {unit}" form for units we don't know how
    to convert (e.g. if PSS ever sends "Days" or "Hours" directly), so we
    never silently drop information.
    """
    if value is None or not unit:
        return "Not specified"

    unit_lower = str(unit).strip().lower()
    if unit_lower not in ("minute", "minutes", "min", "mins"):
        return f"{value} {unit}"

    try:
        total_minutes = int(value)
    except (TypeError, ValueError):
        return f"{value} {unit}"

    if total_minutes < 60:
        return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"

    days, remainder = divmod(total_minutes, _WORKING_DAY_MINUTES)
    hours, minutes = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} working day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return ", ".join(parts) if parts else "0 minutes"


SERVICE_ALIASES = {
    "good moral character": ["Good Moral Certificate", "COG", "good moral"],
    "identification card": ["student ID", "new ID", "lost ID replacement", "ID card"],
    "informative copy of grades": ["copy of grades", "grade slip", "TOR-like grade copy"],
    "correction of grade entry": ["grade correction", "fix grade", "wrong grade", "INC removal"],
    "transcript of records": ["TOR", "transcript"],
    "diploma": ["graduation certificate", "diploma copy"],
    "enrollment": ["enrolment", "pag-enroll", "registration"],
    "cross enrollment": ["cross enrolment", "CE"],
    "shifting": ["change of course", "shift course", "palit course"],
    "leave of absence": ["LOA", "stop schooling", "pahinga sa pag-aaral"],
    "honorable dismissal": ["transfer credential", "HD"],
    "certificate of registration": ["COR", "registration form"],
}


def _build_alias_line(name: str) -> str:
    """Returns an 'Also known as: ...' line for a service name, or ''."""
    name_lower = (name or "").lower()
    for key, aliases in SERVICE_ALIASES.items():
        if key in name_lower:
            return f"Also known as: {', '.join(aliases)}. "
    return ""


def build_text_chunk(svc: dict) -> str:
    """#1 RAG quality factor — the canonical text format that gets embedded."""
    steps = svc.get("processing_steps") or []
    if isinstance(steps, str):
        steps = [steps]
    docs = svc.get("required_documents") or []
    if isinstance(docs, str):
        docs = [docs]

    sla_value = svc.get("sla_target_value")
    sla_unit = svc.get("sla_target_unit")
    sla_text = humanize_sla(sla_value, sla_unit)

    alias_line = _build_alias_line(svc.get("name", ""))

    return (
        f"{alias_line}"
        f"Service: {svc.get('name', '')}. "
        f"Office: {svc.get('office', '')}. "
        f"SLA: {sla_text}. "
        f"Requirements: {'; '.join(docs) if docs else 'None listed'}. "
        f"Steps: {' '.join(f'{i + 1}) {s}' for i, s in enumerate(steps)) if steps else 'None listed'}. "
        f"Output: {svc.get('expected_output') or 'Not specified'}."
    )


def to_embedding_record(svc: dict) -> dict:
    """PSS row → the record shape stored in pgvector / extracted_services.json."""
    return {
        "id": str(svc["id"]),
        "name": svc["name"],
        "office": svc["office"],
        "text_chunk": build_text_chunk(svc),
        "sla_target_value": svc.get("sla_target_value"),
        "sla_target_unit": svc.get("sla_target_unit"),
    }