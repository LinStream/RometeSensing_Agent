from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crud.document import list_documents
from backend.app.db.session import get_db
from backend.app.schemas.document import DocumentResponse

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
async def get_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await list_documents(db, page=page, page_size=page_size)

    return rows