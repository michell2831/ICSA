"""PSS Cloud Backend API — Real-time persistent state for PSS Dashboard, Service Modes, KPIs, Holidays, Periods, and Commitments."""
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Query, Body, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter()

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "pss_cloud_store.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Active SSE subscriber queues for instant sub-second multi-device synchronization
_sync_subscribers: List[asyncio.Queue] = []

def _notify_sync_subscribers(version: int):
    for q in list(_sync_subscribers):
        try:
            q.put_nowait(version)
        except Exception:
            pass

# Default Seed State
INITIAL_STATE = {
    "service_modes": [
        {"id": "sm-1", "name": "Walk-in", "description": "In-person transactions at campus offices", "is_active": True, "created_at": "2026-03-01T08:00:00Z"},
        {"id": "sm-2", "name": "Online", "description": "Services delivered through digital portals or email", "is_active": True, "created_at": "2026-03-01T08:00:00Z"},
        {"id": "sm-3", "name": "Courier", "description": "Delivery or submission via postal/courier services", "is_active": True, "created_at": "2026-03-01T08:00:00Z"},
        {"id": "sm-4", "name": "Hybrid", "description": "Combination of online submission and physical pickup", "is_active": True, "created_at": "2026-03-01T08:00:00Z"},
    ],
    "services": [
        {
            "id": "svc-1",
            "name": "Issuance of Transcript of Records (TOR)",
            "classification": "Complex",
            "sla_target_value": 3,
            "sla_target_unit": "Days",
            "responsible_unit": "Academic Office",
            "status": "ACTIVE",
            "is_active": True,
            "archived": False,
            "intake_documents": "Duly Accomplished Clearance Form\nOfficial Receipt of Payment\n1x1 ID Picture",
            "processing_steps": ["Document Verification", "Payment Verification", "Printing & Signatures", "Release"],
            "expected_output": "Official Transcript of Records",
            "modes": [{"id": "sm-1", "name": "Walk-in"}, {"id": "sm-2", "name": "Online"}],
            "mode_ids": ["sm-1", "sm-2"],
        },
        {
            "id": "svc-2",
            "name": "Application for Graduation & Academic Evaluation",
            "classification": "Highly Technical",
            "sla_target_value": 7,
            "sla_target_unit": "Days",
            "responsible_unit": "Academic Office",
            "status": "ACTIVE",
            "is_active": True,
            "archived": False,
            "intake_documents": "Curriculum Checklist\nBirth Certificate\nForm 137",
            "processing_steps": ["Evaluation", "Audit", "Approval"],
            "expected_output": "Certificate of Candidacy for Graduation",
            "modes": [{"id": "sm-1", "name": "Walk-in"}],
            "mode_ids": ["sm-1"],
        },
        {
            "id": "svc-3",
            "name": "Student Identification Card Issuance",
            "classification": "Simple",
            "sla_target_value": 1,
            "sla_target_unit": "Days",
            "responsible_unit": "Student Affairs Office",
            "status": "ACTIVE",
            "is_active": True,
            "archived": False,
            "intake_documents": "Certificate of Registration (COR)\nBarangay Clearance",
            "processing_steps": ["Data Verification", "Photo Capture", "ID Printing"],
            "expected_output": "RFID Student ID Card",
            "modes": [{"id": "sm-1", "name": "Walk-in"}, {"id": "sm-4", "name": "Hybrid"}],
            "mode_ids": ["sm-1", "sm-4"],
        },
        {
            "id": "svc-4",
            "name": "Issuance of Certificate of Registration (COR)",
            "classification": "Simple",
            "sla_target_value": 1,
            "sla_target_unit": "Days",
            "responsible_unit": "Academic Office",
            "status": "ACTIVE",
            "is_active": True,
            "archived": False,
            "intake_documents": "Enrollment Assessment Form",
            "processing_steps": ["System Verification", "Printing & Stamping"],
            "expected_output": "Official Certificate of Registration",
            "modes": [{"id": "sm-1", "name": "Walk-in"}, {"id": "sm-2", "name": "Online"}],
            "mode_ids": ["sm-1", "sm-2"],
        },
        {
            "id": "svc-5",
            "name": "Medical & Dental Clearance Issuance",
            "classification": "Simple",
            "sla_target_value": 1,
            "sla_target_unit": "Days",
            "responsible_unit": "Administrative Office",
            "status": "ACTIVE",
            "is_active": True,
            "archived": False,
            "intake_documents": "Chest X-Ray Result\nMedical History Form",
            "processing_steps": ["Physical Examination", "Doctor Assessment", "Clearance Signing"],
            "expected_output": "Signed Medical Certificate",
            "modes": [{"id": "sm-1", "name": "Walk-in"}],
            "mode_ids": ["sm-1"],
        },
    ],
    "kpis": [
        {"id": "kpi-1", "service_id": "svc-1", "service_name": "Issuance of Transcript of Records (TOR)", "office": "Academic Office", "category": "Efficiency", "metric": "Resolution Time", "target": "3 Days", "standard": "95% Compliance", "is_active": True},
        {"id": "kpi-2", "service_id": "svc-2", "service_name": "Application for Graduation & Academic Evaluation", "office": "Academic Office", "category": "Quality", "metric": "Accuracy Rate", "target": "7 Days", "standard": "98% Accuracy", "is_active": True},
        {"id": "kpi-3", "service_id": "svc-3", "service_name": "Student Identification Card Issuance", "office": "Student Affairs Office", "category": "Timeliness", "metric": "Turnaround Time", "target": "1 Day", "standard": "90% on-time", "is_active": True},
        {"id": "kpi-4", "service_id": "svc-4", "service_name": "Issuance of Certificate of Registration (COR)", "office": "Academic Office", "category": "Efficiency", "metric": "Processing Speed", "target": "1 Day", "standard": "99% Compliance", "is_active": True},
        {"id": "kpi-5", "service_id": "svc-5", "service_name": "Medical & Dental Clearance Issuance", "office": "Administrative Office", "category": "Quality", "metric": "Patient Satisfaction", "target": "1 Day", "standard": "95% Satisfied", "is_active": True},
    ],
    "holidays": [
        {"id": "hol-1", "name": "New Year's Day", "date": "2026-01-01", "type": "REGULAR", "description": "National Holiday"},
        {"id": "hol-2", "name": "Araw ng Kagitingan", "date": "2026-04-09", "type": "REGULAR", "description": "National Regular Holiday"},
        {"id": "hol-3", "name": "Labor Day", "date": "2026-05-01", "type": "REGULAR", "description": "National Regular Holiday"},
        {"id": "hol-4", "name": "Independence Day", "date": "2026-06-12", "type": "REGULAR", "description": "National Regular Holiday"},
        {"id": "hol-5", "name": "PUP Founding Anniversary", "date": "2026-10-19", "type": "COMPANY", "description": "University Special Holiday"},
    ],
    "periods": [
        {
            "id": "per-1",
            "name": "1st Semester A.Y. 2025-2026",
            "type": "Semester",
            "start_date": "2025-09-01",
            "end_date": "2026-01-31",
            "status": "Open",
            "is_active": True,
        },
        {
            "id": "per-2",
            "name": "2nd Semester A.Y. 2025-2026",
            "type": "Semester",
            "start_date": "2026-02-15",
            "end_date": "2026-07-15",
            "status": "Open",
            "is_active": True,
        },
    ],
    "commitments": [],
}


def _load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        _save_data(INITIAL_STATE)
        return INITIAL_STATE
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all keys exist
            for k, v in INITIAL_STATE.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return INITIAL_STATE


def _save_data(data: dict) -> None:
    try:
        new_version = data.get("version", 1) + 1
        data["version"] = new_version
        data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _notify_sync_subscribers(new_version)
    except Exception as e:
        print(f"[PSS Store] Failed to save data: {e}")


@router.get("/sync/version")
@router.get("/api/sync/version")
def get_sync_version():
    data = _load_data()
    return {
        "version": data.get("version", 1),
        "last_updated": data.get("last_updated", "")
    }


@router.get("/sync/stream")
@router.get("/api/sync/stream")
async def get_sync_stream(request: Request):
    q = asyncio.Queue()
    _sync_subscribers.append(q)

    async def event_generator():
        try:
            data = _load_data()
            yield f"data: {json.dumps({'version': data.get('version', 1)})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    version = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps({'version': version})}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if q in _sync_subscribers:
                _sync_subscribers.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# --- SERVICE MODES ENDPOINTS ---
@router.get("/service-modes")
@router.get("/api/service-modes")
def get_service_modes(include_inactive: Optional[str] = Query(None)):
    data = _load_data()
    modes = data.get("service_modes", [])
    if include_inactive != "true":
        modes = [m for m in modes if m.get("is_active", True)]
    return {"data": modes, "total": len(modes)}


@router.post("/service-modes")
@router.post("/api/service-modes")
def create_service_mode(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    new_mode = {
        "id": f"sm-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "").strip(),
        "description": payload.get("description", "").strip(),
        "is_active": payload.get("is_active", True),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    data["service_modes"].insert(0, new_mode)
    _save_data(data)
    return new_mode


@router.put("/service-modes/{mode_id}")
@router.put("/api/service-modes/{mode_id}")
def update_service_mode(mode_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for m in data["service_modes"]:
        if m["id"] == mode_id:
            m.update({
                "name": payload.get("name", m["name"]),
                "description": payload.get("description", m.get("description", "")),
                "is_active": payload.get("is_active", m.get("is_active", True)),
            })
            _save_data(data)
            return m
    raise HTTPException(status_code=404, detail="Service mode not found")


@router.patch("/service-modes/{mode_id}/toggle")
@router.patch("/api/service-modes/{mode_id}/toggle")
def toggle_service_mode(mode_id: str):
    data = _load_data()
    for m in data["service_modes"]:
        if m["id"] == mode_id:
            m["is_active"] = not m.get("is_active", True)
            _save_data(data)
            return m
@router.delete("/service-modes/{mode_id}")
@router.delete("/api/service-modes/{mode_id}")
def delete_service_mode(mode_id: str):
    data = _load_data()
    original_len = len(data["service_modes"])
    data["service_modes"] = [m for m in data["service_modes"] if m["id"] != mode_id]
    if len(data["service_modes"]) == original_len:
        raise HTTPException(status_code=404, detail="Service mode not found")
    _save_data(data)
    return {"message": "Service mode deleted successfully", "id": mode_id}


# --- SERVICES (CATALOGUE) ENDPOINTS ---
@router.get("/services")
@router.get("/api/services")
def get_services(
    classification: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_archived: Optional[str] = Query(None),
):
    data = _load_data()
    services = data.get("services", [])
    if search:
        s = search.lower()
        services = [x for x in services if s in x.get("name", "").lower() or s in x.get("responsible_unit", "").lower()]
    if classification:
        services = [x for x in services if x.get("classification", "").lower() == classification.lower()]
    if status:
        services = [x for x in services if x.get("status", "").upper() == status.upper()]
    if include_archived != "true":
        services = [x for x in services if not x.get("archived", False)]
    return {"data": services, "total": len(services)}


@router.post("/services")
@router.post("/api/services")
def create_service(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    new_svc = {
        "id": f"svc-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "").strip(),
        "classification": payload.get("classification", "Simple"),
        "sla_target_value": payload.get("sla_target_value", 1),
        "sla_target_unit": payload.get("sla_target_unit", "Days"),
        "responsible_unit": payload.get("responsible_unit", "Academic Office"),
        "status": payload.get("status", "ACTIVE"),
        "is_active": True,
        "archived": False,
        "intake_documents": payload.get("intake_documents", ""),
        "processing_steps": payload.get("processing_steps", []),
        "expected_output": payload.get("expected_output", ""),
        "modes": payload.get("modes", []),
        "mode_ids": payload.get("mode_ids", []),
    }
    data["services"].insert(0, new_svc)
    _save_data(data)
    return new_svc


@router.put("/services/{svc_id}")
@router.put("/api/services/{svc_id}")
def update_service(svc_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for s in data["services"]:
        if s["id"] == svc_id:
            s.update(payload)
            _save_data(data)
            return s
    raise HTTPException(status_code=404, detail="Service not found")


@router.delete("/service-modes/{mode_id}")
@router.delete("/api/service-modes/{mode_id}")
def delete_service_mode(mode_id: str):
    data = _load_data()
    data["service_modes"] = [m for m in data.get("service_modes", []) if m["id"] != mode_id]
    _save_data(data)
    return {"success": True}


@router.patch("/services/{svc_id}/archive")
@router.patch("/api/services/{svc_id}/archive")
def archive_service(svc_id: str):
    data = _load_data()
    for s in data["services"]:
        if s["id"] == svc_id:
            s["archived"] = True
            s["status"] = "INACTIVE"
            s["is_active"] = False
            _save_data(data)
            return s
    raise HTTPException(status_code=404, detail="Service not found")


@router.patch("/services/{svc_id}/activate")
@router.patch("/api/services/{svc_id}/activate")
def activate_service(svc_id: str):
    data = _load_data()
    for s in data["services"]:
        if s["id"] == svc_id:
            s["status"] = "ACTIVE"
            s["is_active"] = True
            s["archived"] = False
            _save_data(data)
            return s
    raise HTTPException(status_code=404, detail="Service not found")


@router.patch("/services/{svc_id}/deactivate")
@router.patch("/api/services/{svc_id}/deactivate")
def deactivate_service(svc_id: str):
    data = _load_data()
    for s in data["services"]:
        if s["id"] == svc_id:
            s["status"] = "INACTIVE"
            s["is_active"] = False
            _save_data(data)
            return s
    raise HTTPException(status_code=404, detail="Service not found")


@router.delete("/services/{svc_id}")
@router.delete("/api/services/{svc_id}")
def delete_service(svc_id: str):
    data = _load_data()
    data["services"] = [s for s in data.get("services", []) if s["id"] != svc_id]
    _save_data(data)
    return {"success": True}


@router.get("/services/{svc_id}/intake-fields")
@router.get("/api/services/{svc_id}/intake-fields")
def get_intake_fields(svc_id: str):
    data = _load_data()
    for s in data.get("services", []):
        if s["id"] == svc_id:
            return s.get("intake_fields", [])
    return []


@router.post("/services/{svc_id}/intake-fields")
@router.post("/api/services/{svc_id}/intake-fields")
def create_intake_field(svc_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for s in data.get("services", []):
        if s["id"] == svc_id:
            fields = s.setdefault("intake_fields", [])
            new_f = {"id": f"fld-{uuid.uuid4().hex[:8]}", **payload}
            fields.append(new_f)
            _save_data(data)
            return new_f
    raise HTTPException(status_code=404, detail="Service not found")


@router.get("/services/{svc_id}/na-flags")
@router.get("/api/services/{svc_id}/na-flags")
def get_na_flags(svc_id: str):
    data = _load_data()
    for s in data.get("services", []):
        if s["id"] == svc_id:
            return s.get("na_flags", [])
    return []


@router.post("/services/{svc_id}/na-flags")
@router.post("/api/services/{svc_id}/na-flags")
def create_na_flag(svc_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for s in data.get("services", []):
        if s["id"] == svc_id:
            flags = s.setdefault("na_flags", [])
            new_flag = {"id": f"flag-{uuid.uuid4().hex[:8]}", **payload}
            flags.append(new_flag)
            _save_data(data)
            return new_flag
    raise HTTPException(status_code=404, detail="Service not found")


@router.delete("/services/{svc_id}/na-flags/{flag_id}")
@router.delete("/api/services/{svc_id}/na-flags/{flag_id}")
def delete_na_flag(svc_id: str, flag_id: str):
    data = _load_data()
    for s in data.get("services", []):
        if s["id"] == svc_id:
            s["na_flags"] = [f for f in s.get("na_flags", []) if f.get("id") != flag_id]
            _save_data(data)
            return {"success": True}
    return {"success": True}


# --- KPIS ENDPOINTS ---
@router.get("/kpis")
@router.get("/api/kpis")
def get_kpis(category: Optional[str] = Query(None), include_inactive: Optional[str] = Query(None)):
    data = _load_data()
    kpis = data.get("kpis", [])
    if category:
        kpis = [k for k in kpis if k.get("category", "").lower() == category.lower()]
    if include_inactive != "true":
        kpis = [k for k in kpis if k.get("is_active", True)]
    return {"data": kpis, "total": len(kpis)}


@router.post("/kpis")
@router.post("/api/kpis")
def create_kpi(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    new_kpi = {
        "id": f"kpi-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name") or payload.get("title") or "",
        "title": payload.get("title") or payload.get("name") or "",
        "category": payload.get("category", "EFFICIENCY"),
        "target_value": payload.get("target_value", 100),
        "unit": payload.get("unit", "%"),
        "service_id": payload.get("service_id"),
        "office": payload.get("office", "Academic Office"),
        "is_active": payload.get("is_active", True),
    }
    data["kpis"].insert(0, new_kpi)
    _save_data(data)
    return new_kpi


@router.put("/kpis/{kpi_id}")
@router.put("/api/kpis/{kpi_id}")
def update_kpi(kpi_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for k in data["kpis"]:
        if k["id"] == kpi_id:
            k.update(payload)
            if "name" in payload and "title" not in payload:
                k["title"] = payload["name"]
            elif "title" in payload and "name" not in payload:
                k["name"] = payload["title"]
            _save_data(data)
            return k
    raise HTTPException(status_code=404, detail="KPI not found")


@router.delete("/kpis/{kpi_id}")
@router.delete("/api/kpis/{kpi_id}")
def delete_kpi(kpi_id: str):
    data = _load_data()
    data["kpis"] = [k for k in data["kpis"] if k["id"] != kpi_id]
    _save_data(data)
    return {"success": True}


# --- HOLIDAYS ENDPOINTS ---
@router.get("/holidays")
@router.get("/api/holidays")
def get_holidays(year: Optional[str] = Query(None), type: Optional[str] = Query(None)):
    data = _load_data()
    holidays = data.get("holidays", [])
    if year:
        holidays = [
            h for h in holidays
            if str(h.get("year", "")) == str(year)
            or str(h.get("date", "")).startswith(str(year))
            or h.get("is_recurring", False)
        ]
    if type:
        holidays = [h for h in holidays if h.get("type", "").lower() == type.lower()]
    return {"data": holidays, "total": len(holidays)}


@router.post("/holidays")
@router.post("/api/holidays")
def create_holiday(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    curr_year = datetime.utcnow().year
    year = payload.get("year", curr_year)
    month = payload.get("month")
    day = payload.get("day")
    date_str = payload.get("holiday_date") or payload.get("date")

    if not date_str and month and day:
        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
    elif date_str and (not month or not day):
        parts = date_str.split("T")[0].split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    new_hol = {
        "id": f"hol-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "").strip(),
        "date": date_str or f"{curr_year}-01-01",
        "holiday_date": date_str or f"{curr_year}-01-01",
        "year": year,
        "month": month,
        "day": day,
        "type": payload.get("type", "REGULAR"),
        "is_recurring": payload.get("is_recurring", False),
    }
    data["holidays"].insert(0, new_hol)
    _save_data(data)
    return new_hol


@router.put("/holidays/{hol_id}")
@router.put("/api/holidays/{hol_id}")
def update_holiday(hol_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for h in data["holidays"]:
        if h["id"] == hol_id:
            h.update(payload)
            if "date" in payload and "holiday_date" not in payload:
                h["holiday_date"] = payload["date"]
            _save_data(data)
            return h
    raise HTTPException(status_code=404, detail="Holiday not found")


@router.delete("/holidays/{hol_id}")
@router.delete("/api/holidays/{hol_id}")
def delete_holiday(hol_id: str):
    data = _load_data()
    data["holidays"] = [h for h in data["holidays"] if h["id"] != hol_id]
    _save_data(data)
    return {"success": True}


# --- PERIODS ENDPOINTS ---
@router.get("/periods")
@router.get("/api/periods")
def get_periods():
    data = _load_data()
    return {"data": data.get("periods", []), "total": len(data.get("periods", []))}


@router.post("/periods")
@router.post("/api/periods")
def create_period(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    p_type = payload.get("period_type") or payload.get("type") or "Semester"
    new_per = {
        "id": f"per-{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "").strip(),
        "type": p_type,
        "period_type": p_type,
        "start_date": payload.get("start_date", ""),
        "end_date": payload.get("end_date", ""),
        "status": payload.get("status", "Open"),
        "is_active": True,
    }
    data["periods"].insert(0, new_per)
    _save_data(data)
    return new_per


@router.put("/periods/{per_id}")
@router.put("/api/periods/{per_id}")
def update_period(per_id: str, payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    for p in data["periods"]:
        if p["id"] == per_id:
            p.update(payload)
            _save_data(data)
            return p
    raise HTTPException(status_code=404, detail="Period not found")


@router.patch("/periods/{per_id}/complete")
@router.patch("/api/periods/{per_id}/complete")
def complete_period(per_id: str):
    data = _load_data()
    for p in data["periods"]:
        if p["id"] == per_id:
            p["status"] = "Closed"
            _save_data(data)
            return p
    raise HTTPException(status_code=404, detail="Period not found")


@router.delete("/periods/{per_id}")
@router.delete("/api/periods/{per_id}")
def delete_period(per_id: str):
    data = _load_data()
    data["periods"] = [p for p in data["periods"] if p["id"] != per_id]
    _save_data(data)
    return {"success": True}


# --- COMMITMENTS & DASHBOARD ENDPOINTS ---
@router.get("/commitments")
@router.get("/api/commitments")
def get_commitments():
    data = _load_data()
    return {"data": data.get("commitments", []), "total": len(data.get("commitments", []))}


@router.post("/commitments")
@router.post("/api/commitments")
def create_commitment(payload: Dict[str, Any] = Body(...)):
    data = _load_data()
    new_comm = {
        "id": f"comm-{uuid.uuid4().hex[:8]}",
        **payload,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    data["commitments"].insert(0, new_comm)
    _save_data(data)
    return new_comm


@router.get("/dashboard/summary")
@router.get("/api/dashboard/summary")
def get_dashboard_summary(office: Optional[str] = Query(None)):
    data = _load_data()
    services = data.get("services", [])
    kpis = data.get("kpis", [])
    periods = data.get("periods", [])
    active_services = [s for s in services if s.get("status") == "ACTIVE" and not s.get("archived")]
    active_kpis = [k for k in kpis if k.get("is_active", True)]
    current_period = periods[0] if periods else {"name": "1st Semester A.Y. 2025-2026", "start_date": "2025-09-01", "end_date": "2026-01-31"}

    return {
        "current_period": current_period,
        "total_services": len(services),
        "active_services": len(active_services),
        "inactive_services": len(services) - len(active_services),
        "total_kpis": len(kpis),
        "active_kpis": len(active_kpis),
        "inactive_kpis": len(kpis) - len(active_kpis),
        "commitments_count": len(data.get("commitments", [])),
    }


@router.get("/planning/hub-summary")
@router.get("/api/planning/hub-summary")
def get_planning_hub_summary():
    data = _load_data()
    return {
        "service_modes_count": len([m for m in data.get("service_modes", []) if m.get("is_active", True)]),
        "kpis_count": len([k for k in data.get("kpis", []) if k.get("is_active", True)]),
        "holidays_count": len(data.get("holidays", [])),
        "periods_count": len(data.get("periods", [])),
    }


@router.get("/planning/opcr-status")
@router.get("/api/planning/opcr-status")
def get_opcr_status(period_id: Optional[str] = Query(None)):
    data = _load_data()
    return {
        "period_id": period_id,
        "offices": [
            {"office": "Academic Office", "status": "COMPLETED", "submitted_at": "2026-03-01T10:00:00Z"},
            {"office": "Student Affairs Office", "status": "PENDING", "submitted_at": None},
            {"office": "Administrative Office", "status": "IN_REVIEW", "submitted_at": "2026-03-02T14:30:00Z"},
        ]
    }


@router.get("/offices")
@router.get("/api/offices")
def get_offices():
    return [
        {"id": "acad", "name": "Academic Office", "code": "ACAD"},
        {"id": "osas", "name": "Student Affairs Office", "code": "OSAS"},
        {"id": "admin", "name": "Administrative Office", "code": "ADMIN"},
    ]
