"""
简单 Agent 路由服务。

这个阶段的 Agent 不做复杂工具调用，也不引入 LangGraph。
它只做一件事：判断当前问题应该走哪条路径。

- chat：普通闲聊，不查知识库；
- rag：知识库问答，调用 RAG 检索和生成。

这就是最小可理解版 Agent：先判断意图，再选择能力。
"""

from typing import Any

from rag.rag_service import RagSummarizeService


class SimpleAgentService:
    def __init__(self, rag_service: RagSummarizeService):
        self.rag_service = rag_service

    def classify_intent(self, question: str) -> str:
        """
        简单规则版意图识别。

        为什么先用规则？
        - 规则最直观，适合初学者理解；
        - 不额外消耗一次大模型调用；
        - 后续可以平滑升级成 LLM 意图识别或 LangGraph。
        """
        q = question.strip()

        # 普通闲聊：不需要检索知识库，直接返回固定说明。
        chat_words = [
            "你好", "您好", "谢谢", "感谢", "你是谁", "你能做什么",
            "介绍一下你", "你可以做什么", "hello", "hi",
        ]

        if q.lower() in [word.lower() for word in chat_words]:
            return "chat"

        # 典型知识库/遥感学习问题：走 RAG。
        rag_keywords = [
            "遥感", "影像", "传感器", "平台", "分辨率", "NDVI",
            "分类", "监督分类", "非监督分类", "辐射校正", "几何校正",
            "大气校正", "地物", "波段", "光谱", "真题", "教材",
            "资料", "文档", "论文", "知识库", "上述", "前面", "这个", "它",
        ]

        if any(keyword in q for keyword in rag_keywords):
            return "rag"

        # 默认走 RAG。
        # 因为这个系统的定位就是“遥感资料问答”，不确定时宁愿查资料。
        return "rag"

    def answer(
        self,
        question: str,
        top_k: int | None = None,
        history: str = "",
    ) -> dict[str, Any]:
        """
        根据意图选择回答路径。
        """
        intent = self.classify_intent(question)

        if intent == "chat":
            return {
                "answer": (
                    "你好，我是遥感资料智能问答助手，可以基于你上传的教材、"
                    "真题和论文资料进行检索问答，也可以帮助你整理适合复习的知识点。"
                ),
                "sources": [],
                "intent": "chat",
            }

        result = self.rag_service.rag_summarize_with_sources(
            query=question,
            top_k=top_k,
            history=history,
        )

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "intent": "rag",
        }
