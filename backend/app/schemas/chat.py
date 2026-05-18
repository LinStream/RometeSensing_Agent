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