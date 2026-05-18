"""
数据库连接配置。

使用 SQLAlchemy 异步连接 MySQL。
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/remote_rag?charset=utf8mb4"


class Base(DeclarativeBase):
    """
    所有 ORM 模型的统一基类。
    """
    pass


async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
)


AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    FastAPI 数据库依赖。

    每次请求：
    1. 创建数据库 session
    2. yield 给接口使用
    3. 请求结束后关闭
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()