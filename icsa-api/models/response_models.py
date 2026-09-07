"""Response schemas — must match /docs/api-contracts.md (SETUP-03)."""
from typing import List, Optional
from pydantic import BaseModel


class MatchedService(BaseModel):
    service_id: Optional[str] = None
    service_name: Optional[str] = None
    office: Optional[str] = None
    confidence: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    matched_service: Optional[str] = None
    matched_service_id: Optional[str] = None
    office: Optional[str] = None
    confidence: float = 0.0
    matched_services: List[MatchedService] = []
    escalated: bool = False
    response_time_ms: int = 0

    session_id: Optional[str] = None


class TopService(BaseModel):
    service_name: str
    office: str
    query_count: int


class QueryVolumePoint(BaseModel):
    date: str
    count: int


class EscalationRate(BaseModel):
    rate: float
    total: int
    escalated: int


class ErrorResponse(BaseModel):
    error: str
    code: int