from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crud.chat import list_chat_messages, list_chat_sessions
from backend.app.db.session import get_db
from backend.app.schemas.chat import ChatMessageResponse, ChatSessionResponse

router = APIRouter(prefix="/api/chats", tags=["Chats"])


@router.get("", response_model=list[ChatSessionResponse])
async def get_chat_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await list_chat_sessions(db, page=page, page_size=page_size)

    return rows


@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    session_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await list_chat_messages(
        db,
        session_id=session_id,
        page=page,
        page_size=page_size,
    )

    return rows