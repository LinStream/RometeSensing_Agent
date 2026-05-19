"""
统一聊天接口。

这是项目唯一的问答主入口：
前端只调用 /api/chat/ask；
后端内部统一进入 LangChain Agent；
RAG 只是 Agent 可以调用的一个工具。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agent.tool_context import get_tool_context, reset_tool_context
from backend.app.crud import chat as chat_crud
from backend.app.db.session import get_db
from backend.app.schemas.chat import ChatAskRequest, ChatAskResponse
from backend.app.services.runtime import react_agent

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatAskResponse)
async def ask(
    req: ChatAskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    统一问答接口。

    流程：
    1. 获取或创建 session；
    2. 读取最近历史；
    3. 调用 LangChain create_agent；
    4. Agent 根据需要调用 RAG tool；
    5. 保存问答记录；
    6. 返回回答。
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空。")

    session = await chat_crud.get_or_create_session(
        db=db,
        session_id=req.session_id,
    )

    recent_messages = await chat_crud.get_recent_chat_messages(
        db=db,
        session_id=session.id,
        limit=6,
    )

    history_text = "\n".join(
        [
            f"用户：{msg.question}\n助手：{msg.answer}"
            for msg in recent_messages
        ]
    )

    reset_tool_context()

    try:
        answer = react_agent.invoke(
            question=req.question,
            history=history_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 调用失败：{str(e)}")

    ctx = get_tool_context()
    sources = ctx.get("sources", [])
    tool_name = ctx.get("tool")

    await chat_crud.create_chat_message(
        db=db,
        session_id=session.id,
        question=req.question,
        answer=answer,
        sources=sources,
    )

    return ChatAskResponse(
        answer=answer,
        sources=sources,
        session_id=session.id,
        tool=tool_name,
        agent_type="langchain_create_agent",
    )
