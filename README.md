# 遥感资料智能问答助手

一个单主线 Agent 项目：

```text
Streamlit 前端
↓
FastAPI /api/chat/ask
↓
LangChain create_agent
↓
RAG Tool
↓
Chroma + 百炼模型
```

## 核心功能

- 上传 PDF/TXT 并写入知识库
- 基于文件 MD5 防止重复上传
- MySQL 保存文档记录和问答历史
- 删除文档时同步删除 MySQL、本地文件和 Chroma 数据
- 使用 LangChain `create_agent` 创建 Agent
- RAG 作为 Agent 的一个工具

## 启动

```bash
uvicorn backend.app.main:app --reload --port 8000
```

```bash
streamlit run frontend/streamlit_app.py
```

## 主接口

```text
POST /api/chat/ask
```

请求：

```json
{
  "question": "什么是遥感？",
  "session_id": null
}
```

响应：

```json
{
  "answer": "...",
  "sources": [],
  "session_id": 1,
  "tool": "rag_summarize",
  "agent_type": "langchain_create_agent"
}
```
