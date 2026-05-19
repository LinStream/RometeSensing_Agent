# 单主线 Agent 重构说明

## 为什么要重构

上一版项目同时存在两个问答入口：

```text
/api/rag/ask
/api/agent/chat
```

前端也出现了多个 tab，导致主线混乱。  
这次重构收敛为一个主入口：

```text
/api/chat/ask
```

核心思想：

```text
用户只管提问；
后端统一进入 LangChain Agent；
RAG 是 Agent 的一个工具。
```

## 现在的主流程

```text
Streamlit
↓
POST /api/chat/ask
↓
backend/app/api/chat.py
↓
读取 session 历史
↓
LangChain create_agent
↓
根据问题决定是否调用 rag_summarize tool
↓
返回 answer
↓
保存 chat_messages
↓
前端展示
```

## 为什么 RAG 作为工具

RAG 本质上是一种能力：

```text
检索 Chroma
↓
拼接 Prompt
↓
调用大模型
↓
返回回答
```

对于 Agent 来说，它就是一个可以调用的工具。

所以现在在 `agent/tools.py` 里定义：

```python
@tool(...)
def rag_summarize(query: str) -> str:
    ...
```

Agent 在需要知识库资料时调用它。

## 为什么不再在主页面放 top_k

`top_k` 是检索参数，不应该暴露给普通用户。  
现在统一使用 `config/chroma.yml` 中的：

```yaml
k: 4
```

如果后面想调整召回数量，只改配置即可。

## 现在哪些功能保留

保留：

```text
文档上传
文档删除
文档去重
MySQL 文档记录
MySQL 问答历史
Agent 问答
RAG 工具
```

弱化：

```text
前端结构化 sources 卡片展示
top_k 滑块
双问答入口
```

## 现在的目录关系

```text
agent/
  react_agent.py      创建 LangChain Agent
  tools.py            定义 rag_summarize 等工具
  tool_context.py     保存工具执行时产生的 sources

backend/app/api/chat.py
  统一聊天接口

backend/app/api/rag.py
  只负责知识库管理：上传、状态、批量加载、清空

rag/
  rag_service.py
  vector_store.py
```

## 面试时怎么讲

可以这样说：

> 我将系统重构为单主线 Agent 架构，前端只保留一个聊天入口，后端统一通过 `/api/chat/ask` 调用 LangChain `create_agent`。RAG 不再作为独立问答入口，而是封装为 Agent 的一个 Tool，由 Agent 根据用户问题决定是否调用。文档上传、去重、删除和历史记录仍由 FastAPI + MySQL 负责，Chroma 负责向量检索。这样既保证了项目主线清晰，也方便后续继续接入 SQL、联网搜索、文档管理等工具。
