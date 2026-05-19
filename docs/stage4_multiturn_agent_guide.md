# 阶段 4：多轮对话与简单 Agent 化说明

本阶段做了两件事：

1. 多轮对话：让历史问答真正参与本轮回答。
2. 简单 Agent 化：在 RAG 前加一层意图识别，判断是否需要查知识库。

---

## 一、为什么要做多轮对话

阶段 2 已经把问答历史保存到了 MySQL，但之前只是“存起来”，回答时没有使用。

所以用户连续问：

```text
第一轮：什么是遥感？
第二轮：它有哪些分类？
```

第二轮里的“它”并不会自动知道指的是“遥感”。

本阶段的改法是：

```text
根据 session_id 查询最近几轮历史
↓
拼成 history_text
↓
传给 RAG prompt
↓
模型结合历史理解追问
```

---

## 二、具体改了哪里

### 1. backend/app/crud/chat.py

新增：

```python
get_recent_chat_messages(db, session_id, limit=6)
```

作用：获取当前会话最近 6 条历史消息，用于 prompt 上下文。

为什么不是查全部？

```text
全部历史可能太长，会增加 token 消耗；
最近几轮通常已经足够支持连续追问。
```

### 2. prompts/rag_summarize.txt

Prompt 增加：

```text
历史对话：
{history}
```

并明确要求模型：如果问题中出现“它、这个、上述、前面提到的”等指代词，要结合历史对话理解。

### 3. rag/rag_service.py

`rag_summarize()` 和 `rag_summarize_with_sources()` 增加 `history` 参数。

调用 chain 时多传：

```python
{
    "input": query,
    "context": context,
    "history": history or "无",
}
```

这样 PromptTemplate 里的 `{history}` 才有值。

### 4. backend/app/api/rag.py

在 ask 接口里：

```text
先 get_or_create_session
再 get_recent_chat_messages
拼 history_text
最后传给 agent_service.answer()
```

---

## 三、为什么要做简单 Agent 化

之前所有问题都会走 RAG。

比如用户问：

```text
你好
```

系统也会去查 Chroma，这没有必要。

所以加一个最小版 Agent：

```text
用户问题
↓
意图识别
↓
chat：普通对话，不查知识库
rag：知识库问答，查 Chroma
```

---

## 四、意图识别是什么

意图识别就是判断用户这句话想让系统做什么。

在本项目中只分两类：

```text
chat：闲聊、打招呼、自我介绍
rag：需要查知识库回答的问题
```

本阶段用规则判断，不用大模型判断。原因：

```text
1. 逻辑简单，便于理解；
2. 不多消耗一次模型调用；
3. 后续可以升级成 LLM 意图识别或 LangGraph。
```

---

## 五、rag/agent_service.py 做了什么

新增 `SimpleAgentService`。

核心方法：

```python
classify_intent(question)
```

根据关键词返回：

```text
chat
rag
```

然后 `answer()` 根据 intent 分流：

```text
intent = chat：直接返回助手介绍，不查 Chroma；
intent = rag：调用 rag_service.rag_summarize_with_sources()。
```

---

## 六、效果

### 多轮对话效果

支持这类连续追问：

```text
用户：什么是遥感？
用户：它有哪些分类？
```

第二问可以结合上一轮理解“它”。

### Agent 效果

问：

```text
你好
```

返回普通问候，`sources=[]`，`intent=chat`。

问：

```text
什么是遥感影像空间分辨率？
```

走知识库检索，`intent=rag`，并返回来源片段。

---

## 七、后续升级方向

1. 将规则意图识别升级为 LLM 意图识别。
2. 给 chat_messages 表增加 intent 字段，统计问题类型。
3. 用 LangGraph 实现更完整的 Agent 工作流。
4. 给多轮对话增加历史摘要，避免长期会话 token 过长。
