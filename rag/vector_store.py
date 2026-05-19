"""
向量库服务。

这个文件尽量参考你提供的 agent 项目写法：
- Chroma
- RecursiveCharacterTextSplitter
- DashScopeEmbeddings（从 model.factory 中导入 embed_model）
- pdf_loader / txt_loader
- md5 去重
"""

import os
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from model.factory import embed_model
from utils.config_handler import chroma_conf
from utils.file_handler import (
    get_file_md5_hex,
    listdir_with_allowed_type,
    pdf_loader,
    txt_loader,
)
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        """
        返回 retriever，供 RagSummarizeService 调用。
        """
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def _md5_store_path(self) -> str:
        """
        md5.text 的绝对路径。
        """
        return get_abs_path(chroma_conf["md5_hex_store"])

    def _check_md5_hex(self, md5_for_check: str) -> bool:
        """
        检查某个文件 md5 是否已经处理过。
        True：处理过
        False：没处理过
        """
        md5_store_path = self._md5_store_path()

        if not os.path.exists(md5_store_path):
            open(md5_store_path, "w", encoding="utf-8").close()
            return False

        with open(md5_store_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.strip() == md5_for_check:
                    return True

        return False

    def _save_md5_hex(self, md5_for_save: str):
        """
        保存已处理文件的 md5。
        """
        with open(self._md5_store_path(), "a", encoding="utf-8") as f:
            f.write(md5_for_save + "\n")

    def _remove_md5_hex(self, md5_for_remove: str):
        """
        删除某个文件的 md5 记录。

        为什么删除文档时要同步删除 md5？
        因为当前项目用 md5.text 判断文件是否已经入库。
        如果只删除 Chroma 和本地文件，但 md5 还留着，
        后面重新上传同一个文件时会被误判为“已经入库”，从而跳过。
        """
        md5_store_path = self._md5_store_path()

        if not os.path.exists(md5_store_path):
            return

        with open(md5_store_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(md5_store_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip() != md5_for_remove:
                    f.write(line)

    def _get_file_documents(self, read_path: str) -> list[Document]:
        """
        根据文件类型调用不同 loader。
        """
        lower_path = read_path.lower()

        if lower_path.endswith(".txt"):
            return txt_loader(read_path)

        if lower_path.endswith(".pdf"):
            return pdf_loader(read_path)

        return []

    def _split_documents(self, documents: list[Document]) -> list[Document]:
        """
        文档切分，并过滤空 chunk。
        """
        split_documents = self.splitter.split_documents(documents)

        split_documents = [
            doc for doc in split_documents
            if isinstance(doc.page_content, str) and doc.page_content.strip()
        ]

        return split_documents

    def load_single_file(self, file_path: str, document_id: int | None = None) -> int:
        """
        加载单个文件到向量库。

        参数：
        - file_path：本地文件路径
        - document_id：MySQL documents 表中的主键 id

        为什么要把 document_id 写进 Chroma metadata？
        因为阶段 3 要支持“删除指定文档”。
        删除时需要根据 document_id 找到 Chroma 中属于该文档的所有 chunks。
        """
        md5_hex = get_file_md5_hex(file_path)

        if not md5_hex:
            raise ValueError(f"无法计算文件 md5：{file_path}")

        if self._check_md5_hex(md5_hex):
            logger.info(f"[加载知识库] {file_path} 内容已经存在知识库内，跳过")
            return 0

        documents = self._get_file_documents(file_path)

        if not documents:
            raise ValueError(f"{file_path} 没有有效文本内容，可能是扫描版 PDF 或空文件")

        # 给每个原始 Document 补充 document_id。
        # splitter 切分后，metadata 会跟随每个 chunk 传递。
        if document_id is not None:
            for doc in documents:
                doc.metadata["document_id"] = document_id

        split_documents = self._split_documents(documents)

        if not split_documents:
            raise ValueError(f"{file_path} 分片后没有有效文本内容")

        self.vector_store.add_documents(split_documents)

        self._save_md5_hex(md5_hex)

        logger.info(f"[加载知识库] {file_path} 内容加载成功，chunks={len(split_documents)}")

        return len(split_documents)

    def load_document(self):
        """
        从 data 文件夹读取所有允许类型文件，批量入库。
        与参考项目保持一致，同时复用 load_single_file。
        """
        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        total = 0

        for path in allowed_files_path:
            try:
                count = self.load_single_file(path)
                total += count
            except Exception as e:
                logger.error(f"[加载知识库] {path} 加载失败：{str(e)}", exc_info=True)
                continue

        return total

    def search(self, query: str, top_k: int | None = None):
        """
        检索接口，返回 Document 列表。
        """
        if top_k is None:
            top_k = chroma_conf["k"]

        retriever = self.vector_store.as_retriever(search_kwargs={"k": top_k})
        return retriever.invoke(query)


    def delete_by_document_id(self, document_id: int):
        """
        根据 document_id 删除 Chroma 中对应的 chunks。

        前提：入库时每个 chunk 的 metadata 中已经写入 document_id。
        """
        self.vector_store.delete(where={"document_id": document_id})

    def remove_md5_by_file_path(self, file_path: str):
        """
        根据文件路径计算 md5，并从 md5.text 中移除。
        """
        md5_hex = get_file_md5_hex(file_path)
        if md5_hex:
            self._remove_md5_hex(md5_hex)

    def count(self) -> int:
        """
        返回当前 collection 中的 chunk 数量。
        """
        return self.vector_store._collection.count()

    def clear(self):
        """
        清空向量库文件和 md5 记录。
        """
        persist_dir = get_abs_path(chroma_conf["persist_directory"])
        md5_store = self._md5_store_path()

        # 删除 Chroma 目录
        if os.path.exists(persist_dir):
            import shutil
            shutil.rmtree(persist_dir)

        os.makedirs(persist_dir, exist_ok=True)

        # 删除 md5 记录
        if os.path.exists(md5_store):
            os.remove(md5_store)

        # 重新初始化 Chroma
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=persist_dir,
        )
