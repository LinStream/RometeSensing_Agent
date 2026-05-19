"""
RAG 总结服务类。

尽量参考你提供的项目写法：
PromptTemplate | print_prompt | chat_model | StrOutputParser

负责：
1. 从向量库检索参考资料；
2. 将参考资料整理成 context；
3. 调用模型生成回答。
"""

from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts


def print_prompt(prompt):
    """
    调试函数：打印最终 prompt。
    与参考项目保持一致。
    """
    print("=" * 20)
    print(prompt.to_string())
    print("=" * 20)
    return prompt


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        """
        LCEL 链：
        PromptTemplate -> print_prompt -> ChatTongyi -> StrOutputParser
        """
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query: str, top_k: int | None = None) -> list[Document]:
        """
        检索相关资料。
        """
        if top_k is None:
            return self.retriever.invoke(query)

        return self.vector_store.search(query, top_k=top_k)

    def _format_context(self, context_docs: list[Document]) -> str:
        """
        将检索到的文档整理成 prompt 里的 context。
        """
        context = ""

        for counter, doc in enumerate(context_docs, start=1):
            doc_name = doc.metadata.get("doc_name") or Path(doc.metadata.get("source", "")).name
            page = doc.metadata.get("page")

            page_text = ""
            if page is not None:
                page_text = f"第{int(page) + 1}页"

            context += (
                f"【参考资料{counter}】"
                f"文档：{doc_name} "
                f"{page_text}\n"
                f"内容：{doc.page_content}\n"
                f"元数据：{doc.metadata}\n\n"
            )

        return context

    def rag_summarize(self, query: str, top_k: int | None = None) -> str:
        """
        RAG 问答主方法。
        """
        context_docs = self.retriever_docs(query, top_k=top_k)

        if not context_docs:
            return "知识库里还没有可检索内容，请先上传或加载资料。"

        context = self._format_context(context_docs)

        return self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )

    def rag_summarize_with_sources(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """
        给 FastAPI 用的版本：
        不仅返回 answer，也返回 sources，便于前端展示引用片段。
        """
        context_docs = self.retriever_docs(query, top_k=top_k)

        if not context_docs:
            return {
                "answer": "知识库里还没有可检索内容，请先上传或加载资料。",
                "sources": [],
            }

        context = self._format_context(context_docs)

        answer = self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )

        sources = []
        for doc in context_docs:
            page = doc.metadata.get("page")
            sources.append(
                {
                    "doc_name": doc.metadata.get("doc_name") or Path(doc.metadata.get("source", "")).name,
                    "page": int(page) + 1 if page is not None else None,
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                }
            )

        return {
            "answer": answer,
            "sources": sources,
        }

    def load_single_file(self, file_path: str, document_id: int | None = None) -> int:
        """
        加载单个文件到知识库。

        document_id 会写入 Chroma metadata，方便后续删除指定文档。
        """
        return self.vector_store.load_single_file(file_path, document_id=document_id)

    def delete_document(self, document_id: int, file_path: str | None = None):
        """
        删除某个文档对应的向量数据。

        参数：
        - document_id：MySQL documents 表中的 id
        - file_path：可选，用于同步清理 md5.text 记录，方便后续重新上传同一文件
        """
        self.vector_store.delete_by_document_id(document_id)

        if file_path:
            self.vector_store.remove_md5_by_file_path(file_path)

    def load_all_documents(self) -> int:
        """
        加载 data 目录下所有允许类型文件。
        """
        return self.vector_store.load_document()

    def stats(self) -> dict[str, Any]:
        """
        知识库状态。
        """
        from utils.config_handler import chroma_conf

        return {
            "collection_name": chroma_conf["collection_name"],
            "chunks_count": self.vector_store.count(),
        }

    def clear(self):
        """
        清空知识库。
        """
        self.vector_store.clear()
