from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ChatMessage, ChatSession

#新建一个聊天会话，默认名称是“新会话”。
async def create_chat_session(
    db: AsyncSession,
    session_name: str = "新会话",
) -> ChatSession:
    session = ChatSession(session_name=session_name)

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session

#如果 session_id 存在且能查到对应会话，则返回该会话；否则新建一个会话并返回。
async def get_or_create_session(
    db: AsyncSession,
    session_id: int | None,
) -> ChatSession:
    if session_id is not None:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )

        session = result.scalar_one_or_none()

        if session is not None:
            return session

    return await create_chat_session(db)

#存储一轮问答（用户提问 + 模型回答 + 引用的来源列表）。
async def create_chat_message(
    db: AsyncSession,
    session_id: int,
    question: str,
    answer: str,
    sources: list[dict],
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        question=question,
        answer=answer,
        sources_json={"sources": sources},
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message

#分页列出所有会话，按 updated_at 倒序（最近更新的在前）。
async def list_chat_sessions(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
):
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count(ChatSession.id)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    rows = result.scalars().all()

    return rows, total

#分页列出某个会话下的所有消息，按 created_at 升序（时间从早到晚），这样前端展示对话历史时顺序正确。
async def list_chat_messages(
    db: AsyncSession,
    session_id: int,
    page: int = 1,
    page_size: int = 20,
):
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )

    rows = result.scalars().all()

    return rows, total