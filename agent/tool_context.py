"""
Agent 工具上下文。

为什么需要它？
LangChain create_agent 的工具通常返回字符串，适合让 Agent 继续推理；
但我们的前端仍然希望拿到 RAG 检索到的 sources，便于后续保存或展示。

这里使用 contextvars，而不是普通全局变量。
原因：
- 普通全局变量在并发请求时可能互相覆盖；
- ContextVar 更适合保存“当前请求/当前任务”的临时上下文。
"""

from contextvars import ContextVar
from typing import Any

_DEFAULT_CONTEXT = {
    "tool": None,
    "sources": [],
}

_tool_context: ContextVar[dict[str, Any]] = ContextVar(
    "tool_context",
    default=_DEFAULT_CONTEXT.copy(),
)


def reset_tool_context():
    """
    每次调用 Agent 前重置上下文。
    """
    _tool_context.set(_DEFAULT_CONTEXT.copy())


def set_tool_context(tool: str | None = None, sources: list[dict] | None = None):
    """
    工具执行时写入当前工具名和结构化来源。
    """
    ctx = _tool_context.get().copy()

    if tool is not None:
        ctx["tool"] = tool

    if sources is not None:
        ctx["sources"] = sources

    _tool_context.set(ctx)


def get_tool_context() -> dict[str, Any]:
    """
    Agent 执行结束后读取工具上下文。
    """
    return _tool_context.get().copy()
