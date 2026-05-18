from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.rag import router as rag_router
from backend.app.api.documents import router as documents_router
from backend.app.api.chats import router as chats_router
from backend.app.db.session import Base, async_engine
from backend.app.db import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动和关闭时执行的逻辑。
    yield 前：启动时执行
    yield 后：关闭时执行
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 如果后面有需要关闭的资源，可以写在这里
    # await async_engine.dispose()


app = FastAPI(
    title="Remote Sensing RAG API",
    description="遥感资料智能问答系统。",
    version="0.2.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router)
app.include_router(documents_router)
app.include_router(chats_router)


@app.get("/health")
def health():
    return {"status": "ok"}