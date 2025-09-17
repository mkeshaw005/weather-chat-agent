from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class SessionSummaryDTO(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str


class MessageDTO(BaseModel):
    role: str
    content: str
    created_at: str


# Explicit exports
__all__ = [
    "ChatRequest",
    "ChatResponse",
    "SessionSummaryDTO",
    "MessageDTO",
]
