from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document


async def create_document(
    db: AsyncSession,
    filename: str,
    file_path: str,
    file_type: str,
    file_md5: str | None = None,
) -> Document:
    document = Document(
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_md5=file_md5,
        status="uploaded",
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


async def get_indexed_document_by_md5(
    db: AsyncSession,
    file_md5: str,
) -> Document | None:
    """
    查询是否已经存在同一份文件内容且成功入库的文档。

    为什么只查 status='indexed'？
    - indexed：说明已经成功进入 Chroma，重复上传应该拦截。
    - failed：说明之前入库失败，允许用户重新上传。
    - uploaded：中间状态，通常不作为已成功文档判断。
    """
    result = await db.execute(
        select(Document).where(
            Document.file_md5 == file_md5,
            Document.status == "indexed",
        )
    )

    return result.scalar_one_or_none()


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


async def get_document_by_id(
    db: AsyncSession,
    document_id: int,
) -> Document | None:
    """
    根据 id 查询单个文档。
    删除文档前需要先查到 file_path。
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )

    return result.scalar_one_or_none()


async def delete_document_by_id(
    db: AsyncSession,
    document_id: int,
) -> None:
    """
    删除 MySQL documents 表中的文档记录。
    """
    await db.execute(
        delete(Document).where(Document.id == document_id)
    )
    await db.commit()
