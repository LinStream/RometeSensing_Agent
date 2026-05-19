from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ChatSessionResponse(BaseModel):
    id: int
    session_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    question: str
    answer: str
    sources_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SourceChunk(BaseModel):
    doc_name: str | None = None
    page: int | None = None
    text: str | None = None
    metadata: dict[str, Any] | None = None


class ChatAskRequest(BaseModel):
    question: str
    session_id: int | None = None


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk] = []
    session_id: int
    tool: str | None = None
    agent_type: str = "langchain_create_agent"
