"""Request schemas — must match /docs/api-contracts.md (SETUP-03)."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatHistoryTurn(BaseModel):
    """One prior turn in the conversation, used by H-01 query rewriting."""
    role: str  # "citizen" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., max_length=500)
    session_id: Optional[str] = None

    chat_history: Optional[List[ChatHistoryTurn]] = None