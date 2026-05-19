"""
FastAPI 请求/响应模型。
"""

from typing import Any
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    top_k: int | None = None
    session_id: int | None = None


class SourceChunk(BaseModel):
    doc_name: str
    page: int | None = None
    text: str
    metadata: dict[str, Any] | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    session_id: int | None = None


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_count: int
    document_id: int | None = None


class StatsResponse(BaseModel):
    collection_name: str
    chunks_count: int
