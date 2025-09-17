from __future__ import annotations

from fastapi import FastAPI, HTTPException
from typing import List

from .service import ChatService, warmup
from .models import (
    ChatRequest,
    ChatResponse,
    SessionSummaryDTO,
    MessageDTO,
)

app = FastAPI(title="Azure Chat Demo API", version="1.0.1")

@app.on_event("startup")
async def on_startup() -> None:
    # Initialize the singleton service and optionally warm up
    ChatService.instance()
    await warmup()


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        answer, session_id = await ChatService.instance().ask(
            req.question, req.session_id
        )
        return ChatResponse(answer=answer, session_id=session_id)
    except Exception as e:  # Log appropriately in production
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=List[SessionSummaryDTO])
async def list_sessions(limit: int = 50, offset: int = 0) -> List[SessionSummaryDTO]:
    repo = ChatService.instance().repository()
    sessions = repo.list_sessions(limit=limit, offset=offset)
    return [
        SessionSummaryDTO(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@app.get("/sessions/{session_id}/messages", response_model=List[MessageDTO])
async def get_session_messages(session_id: str, limit: int = 50) -> List[MessageDTO]:
    repo = ChatService.instance().repository()
    if not repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    msgs = repo.get_messages(session_id, limit=limit)
    return [
        MessageDTO(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in msgs
    ]


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    repo = ChatService.instance().repository()
    if not repo.session_exists(session_id):
        # Deleting a non-existent session is idempotent; return 204-like response
        return {"status": "ok"}
    repo.delete_session(session_id)
    return {"status": "ok"}
