"""
Streamlit 前端。

这个前端只负责：
1. 上传文件；
2. 调用 FastAPI；
3. 展示回答和来源。
"""

import os

import requests
import streamlit as st

# 避免本地代理影响 localhost 请求
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="遥感资料 RAG 问答系统", page_icon="📚", layout="wide")

st.title("📚 遥感资料 RAG 问答系统")


with st.sidebar:
    st.header("系统操作")

    if st.button("测试后端连接"):
        resp = requests.get(
            f"{API_BASE_URL}/health",
            timeout=10,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)
        st.write("返回内容：", resp.text)

    if st.button("查看知识库状态"):
        resp = requests.get(
            f"{API_BASE_URL}/api/rag/stats",
            timeout=30,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)
        st.write("返回内容：", resp.text)

    if st.button("批量加载 data 目录"):
        resp = requests.post(
            f"{API_BASE_URL}/api/rag/load-all",
            timeout=600,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)
        st.write("返回内容：", resp.text)

    if st.button("清空知识库"):
        resp = requests.delete(
            f"{API_BASE_URL}/api/rag/clear",
            timeout=60,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)
        st.write("返回内容：", resp.text)

    if st.button("刷新文档列表"):
        resp = requests.get(
            f"{API_BASE_URL}/api/documents",
            timeout=30,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)

        if resp.status_code == 200:
            st.session_state.documents = resp.json()
        else:
            st.write("返回内容：", resp.text)

    if "documents" in st.session_state:
        st.write("已上传文档：")

        for doc in st.session_state.documents:
            col1, col2 = st.columns([4, 1])

            with col1:
                st.write(
                    f"ID={doc['id']} | {doc['filename']} | "
                    f"chunks={doc['chunk_count']} | status={doc['status']}"
                )

            with col2:
                if st.button("删除", key=f"delete_doc_{doc['id']}"):
                    resp = requests.delete(
                        f"{API_BASE_URL}/api/documents/{doc['id']}",
                        timeout=60,
                        proxies={"http": None, "https": None},
                    )

                    if resp.status_code == 200:
                        st.success(f"文档 {doc['filename']} 删除成功")
                        st.session_state.documents = [
                            item for item in st.session_state.documents
                            if item["id"] != doc["id"]
                        ]
                        st.rerun()
                    else:
                        st.error(resp.text)

    if st.button("查看会话列表"):
        resp = requests.get(
            f"{API_BASE_URL}/api/chats",
            timeout=30,
            proxies={"http": None, "https": None},
        )
        st.write("状态码：", resp.status_code)
        st.write("返回内容：", resp.text)

    if st.button("查看当前会话记录"):
        if st.session_state.session_id is None:
            st.warning("当前还没有会话")
        else:
            resp = requests.get(
                f"{API_BASE_URL}/api/chats/{st.session_state.session_id}/messages",
                timeout=30,
                proxies={"http": None, "https": None},
            )
            st.write("状态码：", resp.status_code)
            st.write("返回内容：", resp.text)

    st.divider()

    st.header("上传资料")
    uploaded_file = st.file_uploader("选择 PDF 或 TXT", type=["pdf", "txt"])

    if st.button("上传并入库", type="primary"):
        if uploaded_file is None:
            st.warning("请先选择文件")
        else:
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "application/octet-stream",
                )
            }

            with st.spinner("正在上传并入库..."):
                resp = requests.post(
                    f"{API_BASE_URL}/api/rag/upload",
                    files=files,
                    timeout=600,
                    proxies={"http": None, "https": None},
                )

            st.write("状态码：", resp.status_code)
            st.write("返回内容：", resp.text)

            if resp.status_code == 200:
                data = resp.json()
                st.success(f"入库成功：{data['filename']}，新增 chunks：{data['chunks_count']}")


st.header("向知识库提问")

question = st.text_input("请输入问题", placeholder="例如：什么是遥感？")
top_k = st.slider("检索片段数量 top_k", min_value=1, max_value=10, value=4)

if st.button("提问", type="primary"):
    if not question.strip():
        st.warning("请先输入问题")
    else:
        if "session_id" not in st.session_state:
            st.session_state.session_id = None
        payload = {
            "question": question,
            "top_k": top_k,
            "session_id": st.session_state.session_id,
        }

        with st.spinner("正在检索并生成回答..."):
            resp = requests.post(
                f"{API_BASE_URL}/api/rag/ask",
                json=payload,
                timeout=600,
                proxies={"http": None, "https": None},
            )
            with st.expander("完整返回内容"):
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

        if resp.status_code == 200:
            data = resp.json()

            st.session_state.session_id = data.get("session_id")

            st.subheader("回答")
            st.write(data["answer"])

            st.subheader("来源片段")
            for i, source in enumerate(data["sources"], start=1):
                page_text = f"｜第 {source['page']} 页" if source.get("page") else ""
                with st.expander(f"来源 {i}｜{source['doc_name']}{page_text}"):
                    st.write(source["text"])
                    st.write("metadata：")
                    st.json(source.get("metadata") or {})
