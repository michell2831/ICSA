"""AI-13 (scaffolded in Week 1 pull-forward): GET /api/analytics/* endpoints.

Week 1: USE_MOCK_ANALYTICS=true -> returns realistic mock data (real PUP
Citizen's Charter service names, per SETUP-03 contract).
Week 2: flip the flag -> parameterized ClickHouse queries run.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from utils import config
from utils.auth import ScopedUser, require_analytics_access, resolve_scoped_office

router = APIRouter()

MOCK_TOP_SERVICES = [
    {"service_name": "Issuance of Medical Certificate", "office": "Administrative", "query_count": 42},
    {"service_name": "Application for New Identification Card", "office": "OSAS", "query_count": 38},
    {"service_name": "Processing of Application for Cross-Enrollment", "office": "Academic", "query_count": 31},
    {"service_name": "Counseling Service", "office": "OSAS", "query_count": 24},
    {"service_name": "Processing of Manual Enrollment", "office": "Academic", "query_count": 19},
]
MOCK_QUERY_VOLUME = [
    {"date": "2026-07-07", "count": 12}, {"date": "2026-07-08", "count": 18},
    {"date": "2026-07-09", "count": 22}, {"date": "2026-07-10", "count": 15},
    {"date": "2026-07-11", "count": 30}, {"date": "2026-07-12", "count": 25},
    {"date": "2026-07-13", "count": 20},
]
MOCK_ESCALATION = {"rate": 12.3, "total": 178, "escalated": 22}
MOCK_AVG_RESPONSE_TIME = {"avg_response_time_ms": 162.4}
MOCK_RECENT_INTERACTIONS = [
    {"query": "How do I get a new student ID?", "matched_service": "Application for New Identification Card", "office": "OSAS", "confidence": 0.88, "response_time_ms": 162, "escalated": False},
    {"query": "What do I need for a medical certificate?", "matched_service": "Issuance of Medical Certificate", "office": "Administrative", "confidence": 0.92, "response_time_ms": 185, "escalated": False},
    {"query": "Paano mag-apply ng cross-enrollment?", "matched_service": "Processing of Application for Cross-Enrollment", "office": "Academic", "confidence": 0.84, "response_time_ms": 210, "escalated": False},
    {"query": "Ano ang kailangan para sa counseling appointment?", "matched_service": "Counseling Service", "office": "OSAS", "confidence": 0.79, "response_time_ms": 140, "escalated": False},
    {"query": "Paano mag-request ng Good Moral Certificate?", "matched_service": "Issuance of Good Moral Certificate", "office": "OSAS", "confidence": 0.70, "response_time_ms": 641, "escalated": True},
]
MOCK_CONFIDENCE_DISTRIBUTION = [
    {"bucket": "0-30% (Low Match)", "count": 3, "color": "#DC2626"},
    {"bucket": "31-50% (Fair Match)", "count": 8, "color": "#F59E0B"},
    {"bucket": "51-70% (Good Match)", "count": 22, "color": "#10B981"},
    {"bucket": "71-100% (High Match)", "count": 45, "color": "#059669"},
]


def _client():
    from clickhouse_driver import Client 
    return Client(
        host=config.CLICKHOUSE_HOST,
        user="default",
        password=config.CLICKHOUSE_PASSWORD,
    )


@router.get("/api/analytics/top-services")
def top_services(
    limit: int = Query(10, ge=1, le=50),
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        data = [s for s in MOCK_TOP_SERVICES if not office or s["office"] == office]
        return data[:limit]
    # Parameterized - office is never interpolated into the SQL string.
    # Exclude empty/null service names so unmatched queries don't appear as a blank bar.
    where = "WHERE matched_service_name != '' AND matched_service_name IS NOT NULL"
    if office:
        where += " AND office = %(office)s"
    rows = _client().execute(
        f"""SELECT matched_service_name AS service_name,
                   argMax(office, created_at) AS service_office,
                   COUNT(*) AS query_count
            FROM icsa.interaction_logs {where}
            GROUP BY service_name
            ORDER BY query_count DESC, service_name ASC LIMIT %(limit)s""",
        {"office": office, "limit": limit},
    )
    return [
        {"service_name": r[0], "office": r[1], "query_count": int(r[2])} for r in rows
    ]


@router.get("/api/analytics/query-volume")
def query_volume(
    period: str = "weekly",
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        return MOCK_QUERY_VOLUME
    where = "AND office = %(office)s" if office else ""
    rows = _client().execute(
        f"""SELECT toDate(created_at) AS date, COUNT(*) AS count
            FROM icsa.interaction_logs
            WHERE created_at >= now() - INTERVAL 7 DAY {where}
            GROUP BY date ORDER BY date""",
        {"office": office},
    )

    from datetime import date, timedelta

    counts_by_date = {str(r[0]): int(r[1]) for r in rows}
    today = date.today()
    full_week = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    return [
        {"date": str(d), "count": counts_by_date.get(str(d), 0)}
        for d in full_week
    ]


@router.get("/api/analytics/escalation-rate")
def escalation_rate(
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        return MOCK_ESCALATION
    where = "WHERE office = %(office)s" if office else ""
    row = _client().execute(
        f"SELECT COUNT(*) AS total, SUM(escalated) AS esc FROM icsa.interaction_logs {where}",
        {"office": office},
    )[0]
    total, esc = int(row[0] or 0), int(row[1] or 0)
    return {
        "rate": round(esc / total * 100, 1) if total > 0 else 0.0,  # div-by-zero safe
        "total": total,
        "escalated": esc,
    }


@router.get("/api/analytics/avg-response-time")
def avg_response_time(
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        return MOCK_AVG_RESPONSE_TIME
    where = "WHERE office = %(office)s" if office else ""
    row = _client().execute(
        f"SELECT AVG(response_time_ms) FROM icsa.interaction_logs {where}",
        {"office": office},
    )[0]
    avg_val = 0.0
    if row and row[0] is not None:
        try:
            val = float(row[0])
            import math
            if not math.isnan(val) and not math.isinf(val):
                avg_val = val
        except (ValueError, TypeError):
            avg_val = 0.0
    return {"avg_response_time_ms": round(avg_val, 1)}


@router.get("/api/analytics/recent-interactions")
def recent_interactions(
    limit: int = Query(10, ge=1, le=50),
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        data = [i for i in MOCK_RECENT_INTERACTIONS if not office or i["office"] == office]
        return data[:limit]
    # Filter out unmatched/off-topic noise (matched_service_name is not null/empty AND confidence >= 0.40)
    where = "WHERE matched_service_name != '' AND matched_service_name IS NOT NULL AND confidence >= 0.40"
    if office:
        where += " AND office = %(office)s"
    rows = _client().execute(
        f"""SELECT query_text, matched_service_name, office, confidence,
                   response_time_ms, escalated, created_at
            FROM icsa.interaction_logs {where}
            ORDER BY created_at DESC LIMIT %(limit)s""",
        {"office": office, "limit": limit},
    )
    return [
        {
            "query": r[0],
            "matched_service": r[1],
            "office": r[2],
            "confidence": round(float(r[3]), 2),
            "response_time_ms": int(r[4]),
            "escalated": bool(r[5]),
            "created_at": str(r[6]),
        }
        for r in rows
    ]


@router.get("/api/analytics/confidence-distribution")
def confidence_distribution(
    office: Optional[str] = None,
    user: ScopedUser = Depends(require_analytics_access),
):
    office = resolve_scoped_office(office, user)
    if config.USE_MOCK_ANALYTICS:
        return MOCK_CONFIDENCE_DISTRIBUTION
    where = "WHERE matched_service_name != '' AND matched_service_name IS NOT NULL"
    if office:
        where += " AND office = %(office)s"
    rows = _client().execute(
        f"""SELECT
                countIf(confidence <= 0.30) AS low,
                countIf(confidence > 0.30 AND confidence <= 0.50) AS weak,
                countIf(confidence > 0.50 AND confidence <= 0.70) AS moderate,
                countIf(confidence > 0.70) AS high
            FROM icsa.interaction_logs {where}""",
        {"office": office},
    )[0]
    return [
        {"bucket": "0-30% (Low Match)", "count": int(rows[0] or 0), "color": "#DC2626"},
        {"bucket": "31-50% (Fair Match)", "count": int(rows[1] or 0), "color": "#F59E0B"},
        {"bucket": "51-70% (Good Match)", "count": int(rows[2] or 0), "color": "#10B981"},
        {"bucket": "71-100% (High Match)", "count": int(rows[3] or 0), "color": "#059669"},
    ]