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

import requests
import streamlit as st

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

API_BASE_URL = "http://localhost:8000"
STREAM_DELAY = 0.006

EXAMPLE_QUESTIONS = [
    "什么是遥感？它有哪些常见分类？",
    "请根据已上传资料，总结遥感影像解译的关键步骤。",
    "帮我整理一份遥感期末复习提纲。",
]

st.set_page_config(
    page_title="遥感资料智能问答助手",
    page_icon="📚",
    layout="wide",
)

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "documents" not in st.session_state:
    st.session_state.documents = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --rs-primary: #256f7b;
            --rs-primary-dark: #164e63;
            --rs-accent: #2f9e8f;
            --rs-bg: #f6faf9;
            --rs-surface: #ffffff;
            --rs-border: #dbe7e5;
            --rs-muted: #64748b;
            --rs-text: #102a43;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(47, 158, 143, 0.08), transparent 32rem),
                linear-gradient(180deg, #f7fbfa 0%, #ffffff 48%);
            color: var(--rs-text);
        }

        .block-container {
            max-width: 1120px;
            padding-top: 2rem;
            padding-bottom: 5rem;
        }

        [data-testid="stSidebar"] {
            background: #f3f8f7;
            border-right: 1px solid var(--rs-border);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--rs-primary-dark);
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.75rem;
        }

        .rs-hero {
            border: 1px solid var(--rs-border);
            background: rgba(255, 255, 255, 0.86);
            border-radius: 8px;
            padding: 1.4rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 10px 28px rgba(15, 76, 92, 0.08);
        }

        .rs-kicker {
            color: var(--rs-primary);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.35rem;
        }

        .rs-title {
            color: var(--rs-primary-dark);
            font-size: clamp(2rem, 4vw, 3rem);
            font-weight: 800;
            line-height: 1.08;
            margin: 0;
        }

        .rs-subtitle {
            color: var(--rs-muted);
            font-size: 1rem;
            line-height: 1.7;
            max-width: 760px;
            margin: 0.75rem 0 0;
        }

        .rs-panel {
            border: 1px solid var(--rs-border);
            background: rgba(255, 255, 255, 0.92);
            border-radius: 8px;
            padding: 1rem;
            margin: 0.75rem 0 1rem;
        }

        .rs-empty {
            border: 1px dashed #b8cfcb;
            background: rgba(255, 255, 255, 0.72);
            border-radius: 8px;
            padding: 1rem;
            color: var(--rs-muted);
            line-height: 1.65;
        }

        .rs-doc-title {
            color: var(--rs-primary-dark);
            font-weight: 700;
            margin-bottom: 0.25rem;
            overflow-wrap: anywhere;
        }

        .rs-doc-meta {
            color: var(--rs-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .rs-tool-note {
            color: var(--rs-muted);
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }

        .rs-welcome {
            border: 1px solid var(--rs-border);
            background: var(--rs-surface);
            border-radius: 8px;
            padding: 1.2rem 1.25rem;
            margin: 0.75rem 0 1rem;
        }

        .rs-welcome h3 {
            color: var(--rs-primary-dark);
            font-size: 1.15rem;
            margin: 0 0 0.45rem;
        }

        .rs-welcome p {
            color: var(--rs-muted);
            line-height: 1.7;
            margin: 0;
        }

        div.stButton > button {
            border-radius: 8px;
            border-color: var(--rs-border);
            color: var(--rs-primary-dark);
            font-weight: 600;
        }

        div.stButton > button:hover {
            border-color: var(--rs-accent);
            color: var(--rs-primary);
        }

        div.stButton > button[kind="primary"] {
            background: var(--rs-primary);
            border-color: var(--rs-primary);
            color: white;
        }

        [data-testid="stChatMessage"] {
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(219, 231, 229, 0.8);
        }

        [data-testid="stChatMessage"] p {
            line-height: 1.75;
        }

        [data-testid="stChatInput"] {
            border-top: 1px solid rgba(219, 231, 229, 0.86);
            background: rgba(246, 250, 249, 0.92);
        }

        @media (max-width: 760px) {
            .block-container {
                padding-top: 1rem;
            }

            .rs-hero {
                padding: 1rem;
            }

            .rs-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <section class="rs-hero">
            <div class="rs-kicker">RemoteSense Agent</div>
            <h1 class="rs-title">遥感资料智能问答助手</h1>
            <p class="rs-subtitle">
                上传教材、论文、真题或复习资料，让 Agent 检索本地知识库并辅助你梳理概念、总结重点和准备复习。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_tool_note(tool: str | None):
    if not tool:
        return

    st.markdown(
        f'<div class="rs-tool-note">检索来源 / 调用工具：{tool}</div>',
        unsafe_allow_html=True,
    )


def request_no_proxy(method: str, url: str, **kwargs):
    """
    统一封装 requests，避免本地代理影响 localhost。
    """
    return requests.request(
        method=method,
        url=url,
        proxies={"http": None, "https": None},
        **kwargs,
    )


def refresh_documents():
    resp = request_no_proxy(
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
        st.header("资料库")
        st.caption("上传 PDF/TXT 后，系统会写入本地知识库供问答检索。")

        st.markdown("### 资料上传")
        uploaded_file = st.file_uploader(
            "上传 PDF 或 TXT",
            type=["pdf", "txt"],
            label_visibility="collapsed",
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
                    resp = request_no_proxy(
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

        st.markdown("### 已入库文档")
        if st.button("刷新文档列表", use_container_width=True):
            refresh_documents()

        if st.session_state.documents:
            for doc in st.session_state.documents:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="rs-doc-title">{doc["filename"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        (
                            '<div class="rs-doc-meta">'
                            f'ID {doc["id"]} · {doc["chunk_count"]} chunks · {doc["status"]}'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        "移除",
                        key=f"delete_doc_{doc['id']}",
                        use_container_width=True,
                    ):
                        resp = request_no_proxy(
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
        else:
            st.markdown(
                '<div class="rs-empty">还没有入库文档。先上传资料，再开始基于资料问答。</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        with st.expander("开发调试", expanded=False):
            st.caption("FastAPI + LangChain Agent + RAG Tool + Chroma + MySQL")

            if st.button("测试后端连接"):
                resp = request_no_proxy(
                    "GET",
                    f"{API_BASE_URL}/health",
                    timeout=10,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("查看知识库状态"):
                resp = request_no_proxy(
                    "GET",
                    f"{API_BASE_URL}/api/rag/stats",
                    timeout=30,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("批量加载 data 目录"):
                resp = request_no_proxy(
                    "POST",
                    f"{API_BASE_URL}/api/rag/load-all",
                    timeout=600,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("清空知识库"):
                resp = request_no_proxy(
                    "DELETE",
                    f"{API_BASE_URL}/api/rag/clear",
                    timeout=60,
                )
                st.write("状态码：", resp.status_code)
                st.write("返回内容：", resp.text)

            if st.button("查看会话列表"):
                resp = request_no_proxy(
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
                    resp = request_no_proxy(
                        "GET",
                        f"{API_BASE_URL}/api/chats/{st.session_state.session_id}/messages",
                        timeout=30,
                    )
                    st.write("状态码：", resp.status_code)
                    st.write("返回内容：", resp.text)


def use_example_question(question: str):
    st.session_state.pending_question = question


def render_welcome():
    st.markdown(
        """
        <div class="rs-welcome">
            <h3>从一个问题开始</h3>
            <p>
                你可以直接提问遥感基础概念，也可以先上传自己的资料，让助手围绕资料内容总结、解释和整理复习重点。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for col, example in zip(cols, EXAMPLE_QUESTIONS):
        with col:
            st.button(
                example,
                key=f"example_{example}",
                use_container_width=True,
                on_click=use_example_question,
                args=(example,),
            )


def render_chat():
    if not st.session_state.messages:
        render_welcome()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            render_tool_note(message.get("tool"))

    question = st.session_state.pending_question or st.chat_input(
        "请输入问题，例如：什么是遥感？它有哪些分类？"
    )
    st.session_state.pending_question = None

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
                resp = request_no_proxy(
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

                render_tool_note(tool)

                # 伪流式输出：
                # 后端仍然一次性返回完整 answer；前端拿到 answer 后，
                # 用 Streamlit 原生 write_stream() 按字符逐步展示。
                # 这种写法和你之前学的 st.chat_message + write_stream 风格一致。
                def fake_stream(text: str):
                    for char in text:
                        time.sleep(STREAM_DELAY)
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


apply_theme()
render_header()
render_sidebar()
render_chat()
