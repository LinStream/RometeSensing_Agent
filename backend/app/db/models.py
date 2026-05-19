"""
数据库表模型。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class Document(Base):
    """
    文档表。

    记录用户上传过哪些文件，以及入库状态。
    """

    __tablename__ = "documents"

    __table_args__ = (
        Index("idx_documents_file_md5", "file_md5"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    file_type: Mapped[str] = mapped_column(String(50), default="pdf")

    # 文件内容 MD5，用来判断是否重复上传同一份文件。
    # 注意：用 MD5 判断的是“文件内容是否相同”，比只看文件名更可靠。
    file_md5: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    # uploaded / indexed / failed

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )


class ChatSession(Base):
    """
    会话表。
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_name: Mapped[str] = mapped_column(String(255), default="新会话")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )


class ChatMessage(Base):
    """
    问答记录表。
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_sessions.id"),
        nullable=False,
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)

    answer: Mapped[str] = mapped_column(Text, nullable=False)

    sources_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)