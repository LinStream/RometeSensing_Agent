from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document


async def create_document(
    db: AsyncSession,
    filename: str,
    file_path: str,
    file_type: str,
) -> Document:
    document = Document(
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        status="uploaded",
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


async def update_document_success(
    db: AsyncSession,
    document_id: int,
    chunk_count: int,
):
    stmt = (
        update(Document)
        .where(Document.id == document_id)
        .values(
            chunk_count=chunk_count,
            status="indexed",
            error_message=None,
        )
    )

    await db.execute(stmt)
    await db.commit()


async def update_document_failed(
    db: AsyncSession,
    document_id: int,
    error_message: str,
):
    stmt = (
        update(Document)
        .where(Document.id == document_id)
        .values(
            status="failed",
            error_message=error_message,
        )
    )

    await db.execute(stmt)
    await db.commit()


async def list_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
):
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count(Document.id)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    rows = result.scalars().all()

    return rows, total