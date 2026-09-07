# ICSA API Contracts (SETUP-03)

Co-authored by: AI Specialist (Jlhan) + FE Developer (Paula). DE (Stephanie) reviews DB fields. PM (Ralph) validates scope.
**Both Jlhan and Paula must acknowledge this document in the group chat before FE-02 / AI-06 start.**

Base URL (local dev): `http://localhost:8000`

## Standardized error format (all endpoints)
```json
{ "error": "string", "code": 400 }
```

---

## 1. POST /api/chat
Citizen question → grounded AI answer.

**Request**
| Field | Type | Required | Notes |
|---|---|---|---|
| query | string | ✅ | 1–500 chars |
| session_id | string | ❌ | auto-generated (uuid4) if omitted |

```json
{ "query": "What do I need for a medical certificate?", "session_id": "optional-uuid" }
```

**Response 200**
| Field | Type | Notes |
|---|---|---|
| answer | string | plain-language grounded answer |
| matched_service | string \| null | top pgvector match |
| matched_service_id | string \| null | PSS service UUID |
| office | string \| null | Academic / Administrative / OSAS |
| confidence | number | cosine similarity of top match (0–1) |
| matched_services | array | array of all retrieved matches above threshold ({service_id, service_name, office, confidence}) |
| escalated | boolean | true when confidence < 0.50 or answer says "please visit" |
| response_time_ms | number | full pipeline duration |

```json
{
  "answer": "To get a Medical Certificate... SLA: 30 Minutes.",
  "matched_service": "Issuance of Medical Certificate",
  "matched_service_id": "0d5a…",
  "office": "Administrative",
  "confidence": 0.87,
  "matched_services": [
    {
      "service_id": "0d5a…",
      "service_name": "Issuance of Medical Certificate",
      "office": "Administrative",
      "confidence": 0.87
    }
  ],
  "escalated": false,
  "response_time_ms": 1240
}
```

**Errors**: 400 `Query cannot be empty` · 500 `Internal server error. Please try again.`

---

## 2. GET /api/analytics/top-services?limit=10&office=Academic
**Response 200** — array of:
```json
[{ "service_name": "Issuance of Medical Certificate", "office": "Administrative", "query_count": 42 }]
```

## 3. GET /api/analytics/query-volume?period=weekly&office=OSAS
**Response 200** — array of:
```json
[{ "date": "2026-07-07", "count": 12 }]
```

## 4. GET /api/analytics/escalation-rate?office=Academic
**Response 200**
```json
{ "rate": 12.3, "total": 178, "escalated": 22 }
```
`rate` is a percentage, division-by-zero safe (`0.0` when `total` = 0).

## 5. GET /api/health
```json
{ "status": "ok", "version": "1.0.0" }
```

---

`office` query param is optional on all analytics endpoints; values: `Academic`, `Administrative`, `OSAS`. Omit for all offices.

---

## 6. GET /api/services?office=Academic&limit=100
Live list of active services **straight from the PSS database (read-only SELECT)**.
```json
{
  "count": 77,
  "services": [
    {
      "id": "uuid", "name": "…", "office": "…", "classification": "…",
      "sla_target_value": 30, "sla_target_unit": "Minutes",
      "processing_steps": ["…"], "required_documents": ["…"], "expected_output": "…"
    }
  ]
}
```
**Errors**: 503 `PSS_DB_URL not set…` (credential pending) · 502 `PSS database unreachable`

## 7. GET /api/services/count
```json
{ "total": 77, "per_office": { "Campus Academic Office": 14, "Campus Administrative Office": 36 } }
```
Used for the DE-08 data-validation report (PSS count vs pgvector count).

## 8. POST /api/admin/reindex → 202
On-demand ETL: **PSS → embeddings → pgvector** in a background thread.
```json
{ "status": "started", "check": "/api/admin/reindex/status" }
```
409 kapag may tumatakbo pang reindex.

## 9. GET /api/admin/reindex/status
```json
{ "status": "done", "detail": "Upserted 77 services from PSS into pgvector.", "started_at": "…", "finished_at": "…" }
```
`status`: `never_run` | `running` | `done` | `failed`
