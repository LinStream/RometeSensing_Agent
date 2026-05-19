"""
FastAPI RAG 接口层。

接口层只负责：
1. 接收前端请求；
2. 做基础校验；
3. 调用 RagSummarizeService；
4. 返回响应。
"""

import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.schemas.rag import AskRequest, AskResponse, StatsResponse, UploadResponse
from rag.rag_service import RagSummarizeService
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.crud import document as document_crud
from backend.app.crud import chat as chat_crud

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# 简单单例：服务启动后复用一个 RAG 服务实例
rag_service = RagSummarizeService()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    allowed_types = tuple(chroma_conf["allow_knowledge_file_type"])

    if not file.filename.lower().endswith(allowed_types):
        raise HTTPException(
            status_code=400,
            detail=f"目前只支持以下文件类型：{allowed_types}",
        )

    save_path = get_abs_path(f"{chroma_conf['data_path']}/{file.filename}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    document = await document_crud.create_document(
        db=db,
        filename=file.filename,
        file_path=save_path,
        file_type=file.filename.split(".")[-1].lower(),
    )

    try:
        chunks_count = rag_service.load_single_file(save_path, document_id=document.id)

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

@router.post("/ask", response_model=AskResponse)
async def ask(
    req: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    向知识库提问。
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空。")

    session = await chat_crud.get_or_create_session(
        db=db,
        session_id=req.session_id,
    )

    try:
        result = rag_service.rag_summarize_with_sources(
            req.question,
            top_k=req.top_k,
        )

        await chat_crud.create_chat_message(
            db=db,
            session_id=session.id,
            question=req.question,
            answer=result["answer"],
            sources=result["sources"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败：{str(e)}")

    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        session_id=session.id,
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
