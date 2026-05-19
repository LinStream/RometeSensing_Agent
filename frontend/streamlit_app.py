"""
Streamlit 前端。

单主线版本：
- 主页面只有一个聊天入口；
- 后端统一调用 /api/chat/ask；
- RAG 不再作为前端单独入口，而是 Agent 的一个工具；
- 文档管理放在侧边栏；
- 调试功能收进 expander。
"""

import os
import time
from urllib.parse import urlparse
import requests
import streamlit as st

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="遥感资料智能问答助手",
    page_icon="📚",
    layout="wide",
)

st.title("📚 遥感资料智能问答助手")
st.caption("FastAPI + LangChain Agent + RAG Tool + Chroma + MySQL")

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "documents" not in st.session_state:
    st.session_state.documents = []


def is_local_url(url: str) -> bool:
    host = urlparse(url).hostname
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def request_api(method: str, url: str, use_proxy: bool | None = None, **kwargs):
    if use_proxy is None:
        use_proxy = not is_local_url(url)

    session = requests.Session()
    session.trust_env = use_proxy

    return session.request(
        method=method,
        url=url,
        **kwargs,
    )

def refresh_documents():
    resp = request_api(
        "GET",
        f"{API_BASE_URL}/api/documents",
        timeout=30,
    )

    if resp.status_code == 200:
        st.session_state.documents = resp.json()
    else:
        st.error(resp.text)


def render_sidebar():
    with st.sidebar:
        st.header("文档管理")

        uploaded_file = st.file_uploader(
            "上传 PDF 或 TXT",
            type=["pdf", "txt"],
        )

        if st.button("上传并入库", type="primary", use_container_width=True):
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

                with st.spinner("正在上传并写入知识库..."):
                    resp = request_api(
                        "POST",
                        f"{API_BASE_URL}/api/rag/upload",
                        files=files,
                        timeout=600,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    st.success(
                        f"入库成功：{data['filename']}，chunks={data['chunks_count']}"
                    )
                    refresh_documents()
                else:
                    st.error(resp.text)

        if st.button("刷新文档列表", use_container_width=True):
            refresh_documents()

        if st.session_state.documents:
            st.subheader("已上传文档")

            for doc in st.session_state.documents:
                with st.container(border=True):
                    st.write(f"**{doc['filename']}**")
                    st.caption(
                        f"ID={doc['id']} | chunks={doc['chunk_count']} | status={doc['status']}"
                    )

                    if st.button("删除", key=f"delete_doc_{doc['id']}"):
                        resp = request_api(
                            "DELETE",
                            f"{API_BASE_URL}/api/documents/{doc['id']}",
                            timeout=60,
                        )

                        if resp.status_code == 200:
                            st.success("删除成功")
                            refresh_documents()
                            st.rerun()
                        else:
                            st.error(resp.text)

        st.divider()

        with st.expander("开发调试", expanded=False):
            if st.button("测试后端连接"):
                resp = request_api(
                    "GET",
                    f"{API_BASE_URL}/health",
                    timeout=10,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("查看知识库状态"):
                resp = request_api(
                    "GET",
                    f"{API_BASE_URL}/api/rag/stats",
                    timeout=30,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("批量加载 data 目录"):
                resp = request_api(
                    "POST",
                    f"{API_BASE_URL}/api/rag/load-all",
                    timeout=600,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("清空知识库"):
                resp = request_api(
                    "DELETE",
                    f"{API_BASE_URL}/api/rag/clear",
                    timeout=60,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("查看会话列表"):
                resp = request_api(
                    "GET",
                    f"{API_BASE_URL}/api/chats",
                    timeout=30,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("查看当前会话记录"):
                if st.session_state.session_id is None:
                    st.warning("当前还没有会话")
                else:
                    resp = request_api(
                        "GET",
                        f"{API_BASE_URL}/api/chats/{st.session_state.session_id}/messages",
                        timeout=30,
                    )
                    st.write("状态码：", resp.status_code)
                    st.write("返回内容：", resp.text)


def render_chat():
    st.subheader("智能问答")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("tool"):
                st.caption(f"调用工具：{message['tool']}")

    question = st.chat_input("请输入问题，例如：什么是遥感？它有哪些分类？")

    if question:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        with st.chat_message("user"):
            st.markdown(question)

        payload = {
            "question": question,
            "session_id": st.session_state.session_id,
        }

        with st.chat_message("assistant"):
            with st.spinner("Agent 正在思考并选择工具..."):
                resp = request_api(
                    "POST",
                    f"{API_BASE_URL}/api/chat/ask",
                    json=payload,
                    timeout=600,
                )

            if resp.status_code == 200:
                data = resp.json()

                st.session_state.session_id = data.get("session_id")

                answer = data["answer"]
                tool = data.get("tool")

                if tool:
                    st.caption(f"调用工具：{tool}")

                # 伪流式输出：
                # 后端仍然一次性返回完整 answer；前端拿到 answer 后，
                # 用 Streamlit 原生 write_stream() 按字符逐步展示。
                # 这种写法和你之前学的 st.chat_message + write_stream 风格一致。
                def fake_stream(text: str):
                    for char in text:
                        time.sleep(0.01)
                        yield char

                streamed_answer = st.write_stream(fake_stream(answer))

                # write_stream 会返回最终拼接后的字符串，直接存入聊天历史。
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": streamed_answer,
                        "tool": tool,
                    }
                )
            else:
                st.error(resp.text)


render_sidebar()
render_chat()
