from __future__ import annotations

from fastapi import FastAPI, HTTPException, APIRouter
from typing import List

from .service import MathChatService, SommelierChatService, WeatherChatService, warmup
from .models import (
    ChatRequest,
    ChatResponse,
    SessionSummaryDTO,
    MessageDTO,
)
from .auth import AuthDependency

app = FastAPI(title="Azure Chat Demo API", version="1.0.1")

# Router with authentication required on all endpoints
router = APIRouter(dependencies=[AuthDependency])


@app.on_event("startup")
async def on_startup() -> None:
    # Initialize the singleton service and optionally warm up
    WeatherChatService.instance()
    SommelierChatService.instance()
    await warmup()


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        answer, session_id = await WeatherChatService.instance().ask(
            req.question, req.session_id
        )
        return ChatResponse(answer=answer, session_id=session_id)
    except Exception as e:  # Log appropriately in production
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/somelier/chat", response_model=ChatResponse)
async def somelier_chat(req: ChatRequest) -> ChatResponse:
    try:
        answer, session_id = await SommelierChatService.instance().ask(
            req.question, req.session_id
        )
        return ChatResponse(answer=answer, session_id=session_id)
    except Exception as e:  # Log appropriately in production
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/math/chat", response_model=ChatResponse)
async def math_chat(req: ChatRequest) -> ChatResponse:
    try:
        answer, session_id = await MathChatService.instance().ask(
            req.question, req.session_id
        )
        return ChatResponse(answer=answer, session_id=session_id)
    except Exception as e:  # Log appropriately in production
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[SessionSummaryDTO])
async def list_sessions(limit: int = 50, offset: int = 0) -> List[SessionSummaryDTO]:
    repo = WeatherChatService.instance().repository()
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


@router.get("/sessions/{session_id}/messages", response_model=List[MessageDTO])
async def get_session_messages(session_id: str, limit: int = 50) -> List[MessageDTO]:
    repo = WeatherChatService.instance().repository()
    if not repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    msgs = repo.get_messages(session_id, limit=limit)
    return [
        MessageDTO(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in msgs
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    repo = WeatherChatService.instance().repository()
    if not repo.session_exists(session_id):
        # Deleting a non-existent session is idempotent; return 204-like response
        return {"status": "ok"}
    repo.delete_session(session_id)
    return {"status": "ok"}


# Include the secured router
app.include_router(router)
