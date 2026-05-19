"""
LangChain Agent 工具集合。

当前项目只保留一条主线：
用户问题 -> LangChain create_agent -> 根据需要调用工具。

这里把 RAG 封装成 Agent 的一个 tool。
后面如果要接入 SQL、联网搜索、文档管理等工具，也从这里继续添加。
"""

from langchain_core.tools import tool

from agent.tool_context import set_tool_context


def build_agent_tools(rag_service):
    """
    构建工具列表。

    这里使用闭包把 rag_service 注入到 tool 函数中，
    避免 tools.py 直接 import runtime 导致循环依赖。
    """

    @tool(description="用于回答遥感教材、真题、论文、知识库资料相关问题。输入应为用户的自然语言问题。")
    def rag_summarize(query: str) -> str:
        """
        RAG 知识库问答工具。

        注意：
        - Agent tool 返回值主要给大模型继续组织最终回答，所以这里返回字符串；
        - 结构化 sources 通过 tool_context 保存，供 FastAPI 接口返回和 MySQL 保存。
        """
        result = rag_service.rag_summarize_with_sources(query=query)

        sources = result.get("sources", [])
        set_tool_context(tool="rag_summarize", sources=sources)

        source_lines = []
        for i, source in enumerate(sources, start=1):
            doc_name = source.get("doc_name") or "未知文档"
            page = source.get("page")
            page_text = f"，第{page}页" if page is not None else ""
            source_lines.append(f"{i}. {doc_name}{page_text}")

        if source_lines:
            source_text = "\n".join(source_lines)
        else:
            source_text = "无"

        return (
            f"{result.get('answer', '')}\n\n"
            f"参考来源：\n{source_text}"
        )

    @tool(description="用于处理问候、感谢、自我介绍等不需要检索知识库的普通对话。")
    def chat_direct(query: str) -> str:
        """
        普通对话工具。

        这个工具不查 Chroma，只返回系统能力说明。
        """
        set_tool_context(tool="chat_direct", sources=[])

        return (
            "你好，我是遥感资料智能问答助手。"
            "你可以上传遥感教材、真题、论文或笔记，我会基于资料进行问答。"
        )

    return [rag_summarize, chat_direct]
