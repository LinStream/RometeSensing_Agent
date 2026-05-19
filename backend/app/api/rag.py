"""
知识库管理接口。

注意：
本项目现在只有一个问答主入口：/api/chat/ask。
这个文件只保留知识库相关管理能力：
- 上传文件
- 查看知识库状态
- 批量加载
- 清空知识库
"""

import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crud import document as document_crud
from backend.app.db.session import get_db
from backend.app.schemas.rag import StatsResponse, UploadResponse
from backend.app.services.runtime import rag_service
from utils.config_handler import chroma_conf
from utils.file_handler import get_file_md5_hex
from utils.path_tool import get_abs_path

router = APIRouter(prefix="/api/rag", tags=["Knowledge Base"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上传知识库文件。

    这里不负责问答，只负责：
    1. 保存文件；
    2. 计算 MD5 并查重；
    3. 创建 documents 记录；
    4. 写入 Chroma；
    5. 更新文档状态。
    """
    allowed_types = tuple(chroma_conf["allow_knowledge_file_type"])

    if not file.filename.lower().endswith(allowed_types):
        raise HTTPException(
            status_code=400,
            detail=f"目前只支持以下文件类型：{allowed_types}",
        )

    save_path = get_abs_path(f"{chroma_conf['data_path']}/{file.filename}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_md5 = get_file_md5_hex(save_path)

    if not file_md5:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail="文件 MD5 计算失败，无法入库。")

    existed_document = await document_crud.get_indexed_document_by_md5(
        db=db,
        file_md5=file_md5,
    )

    if existed_document is not None:
        if os.path.exists(save_path):
            os.remove(save_path)

        raise HTTPException(
            status_code=409,
            detail=(
                f"该文件内容已上传并成功入库，"
                f"文档ID={existed_document.id}，文件名={existed_document.filename}"
            ),
        )

    document = await document_crud.create_document(
        db=db,
        filename=file.filename,
        file_path=save_path,
        file_type=file.filename.split(".")[-1].lower(),
        file_md5=file_md5,
    )

    try:
        chunks_count = rag_service.load_single_file(
            save_path,
            document_id=document.id,
            file_md5=file_md5,
        )

        await document_crud.update_document_success(
            db=db,
            document_id=document.id,
            chunk_count=chunks_count,
        )

    except Exception as e:
        await document_crud.update_document_failed(
            db=db,
            document_id=document.id,
            error_message=str(e),
        )

        raise HTTPException(status_code=500, detail=f"文件入库失败：{str(e)}")

    return UploadResponse(
        message="文件上传并入库成功",
        filename=file.filename,
        chunks_count=chunks_count,
        document_id=document.id,
    )


@router.get("/stats", response_model=StatsResponse)
def stats():
    """
    查看知识库状态。
    """
    try:
        return StatsResponse(**rag_service.stats())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取知识库状态失败：{str(e)}")


@router.post("/load-all")
def load_all():
    """
    批量加载 data 目录中的所有知识文件。
    """
    try:
        chunks_count = rag_service.load_all_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量加载失败：{str(e)}")

    return {
        "message": "批量加载完成",
        "chunks_count": chunks_count,
    }


@router.delete("/clear")
def clear():
    """
    清空知识库。
    """
    try:
        rag_service.clear()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空知识库失败：{str(e)}")

    return {"message": "知识库已清空"}
