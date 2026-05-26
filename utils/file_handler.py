"""
文件处理工具，尽量沿用参考项目的写法。

包括：
1. 计算文件 MD5，用于防止重复入库；
2. 列出允许类型的知识库文件；
3. 使用 LangChain Loader 加载 PDF / TXT。
"""

import hashlib
import os
from typing import Iterable

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from utils.config_handler import chroma_conf
from utils.logger_handler import logger


def get_file_md5_hex(filepath: str):
    """
    获取文件 md5 十六进制字符串。
    用于判断文件是否已经入库过。
    """
    if not os.path.exists(filepath):
        logger.error(f"[md5计算] 文件 {filepath} 不存在")
        return None

    if not os.path.isfile(filepath):
        logger.error(f"[md5计算] 路径 {filepath} 不是文件")
        return None

    md5_obj = hashlib.md5()
    chunk_size = 4096

    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except Exception as e:
        logger.error(f"[md5计算] 计算文件 {filepath} md5 失败：{str(e)}")
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> tuple[str, ...]:
    """
    返回文件夹中允许后缀的文件路径。
    """
    files = []

    if not os.path.isdir(path):
        logger.error(f"[listdir_with_allowed_type] {path} 不是文件夹")
        return tuple(files)

    for f in os.listdir(path):
        if f.lower().endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files)


def pdf_loader(filepath: str, passwd=None) -> list[Document]:
    """
    使用 LangChain PyPDFLoader 加载 PDF。
    如果提取文本为空或过少，自动降级到 qwen-vl OCR 识别扫描版 PDF。
    """
    docs = PyPDFLoader(filepath, passwd).load()
    for doc in docs:
        doc.metadata["doc_name"] = os.path.basename(filepath)

    if _should_use_pdf_ocr(docs):
        logger.info(f"[PDF加载] {filepath} 文本层为空或过少，尝试 OCR 识别")
        docs = pdf_ocr_loader(filepath)

    return docs


def _should_use_pdf_ocr(docs: list[Document]) -> bool:
    """
    判断 PDF 是否需要 OCR 兜底。

    PyPDFLoader 对扫描版 PDF 往往会返回“页数存在但 page_content 为空”的
    Document 列表，所以不能只用 not docs 判断。
    """
    ocr_conf = chroma_conf.get("ocr", {})
    if not ocr_conf.get("enabled", True):
        return False

    min_text_chars = int(ocr_conf.get("min_text_chars", 50))
    text_chars = sum(
        len(doc.page_content.strip())
        for doc in docs
        if isinstance(doc.page_content, str)
    )

    return text_chars < min_text_chars


def pdf_ocr_loader(filepath: str) -> list[Document]:
    """
    对扫描版 PDF 使用 qwen-vl 视觉模型识别文字。

    流程：
    1. PyMuPDF 打开 PDF，逐页转为图片
    2. 图片编码为 base64，发给 qwen-vl 识别
    3. 组装为 Document 列表（格式与 PyPDFLoader 一致）

    为什么用延迟导入？
    dashscope.MultiModalConversation 在文件顶部不需要导入，
    因为只有扫描版 PDF 才会调用这个函数，正常 PDF 不会触发。
    """
    import base64

    import fitz
    from dashscope import MultiModalConversation

    ocr_conf = chroma_conf.get("ocr", {})
    model_name = ocr_conf.get("model", "qwen-vl-max")
    dpi = int(ocr_conf.get("dpi", 200))

    doc = fitz.open(filepath)
    docs = []

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode()
            data_url = f"data:image/png;base64,{b64}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": data_url},
                        {"text": "请识别这张图片中的所有文字内容，保持原有格式和段落结构，只输出识别到的文字，不要添加任何解释或说明。"},
                    ],
                }
            ]

            response = MultiModalConversation.call(
                model=model_name,
                messages=messages,
            )

            if response.status_code == 200:
                text = _extract_ocr_text(response)

                if text.strip():
                    docs.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": filepath,
                                "page": page_num,
                                "doc_name": os.path.basename(filepath),
                            },
                        )
                    )
            else:
                logger.error(
                    f"[OCR] 第 {page_num + 1} 页识别失败: {response.message}"
                )
    finally:
        doc.close()

    logger.info(f"[OCR] {filepath} 识别完成，共 {len(docs)} 页有文字内容")
    return docs


def _extract_ocr_text(response) -> str:
    """
    兼容 DashScope 多模态接口返回的文本结构。
    """
    content = response.output.choices[0].message.content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    return str(content)


def txt_loader(filepath: str) -> list[Document]:
    """
    使用 LangChain TextLoader 加载 TXT。
    """
    docs = TextLoader(filepath, encoding="utf-8").load()
    for doc in docs:
        doc.metadata["doc_name"] = os.path.basename(filepath)
    return docs
