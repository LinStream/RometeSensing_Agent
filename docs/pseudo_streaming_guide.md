# 伪流式输出说明

本项目当前实现的是**前端伪流式输出**。

## 为什么这样做

真正的流式输出需要后端使用 `StreamingResponse` 或 Server-Sent Events，并且 Agent/LLM 调用链也要支持流式返回。当前项目的后端 `/api/chat/ask` 已经能稳定返回完整回答，所以为了不破坏现有 Agent 主线，先在 Streamlit 前端实现伪流式。

## 怎么做

后端仍然一次性返回完整：

```json
{
  "answer": "完整回答内容...",
  "session_id": 1,
  "tool": "rag_summarize"
}
```

前端拿到 `answer` 后，不是一次性 `st.markdown(answer)`，而是：

```python
answer_placeholder = st.empty()
displayed_answer = ""

for char in answer:
    displayed_answer += char
    answer_placeholder.markdown(displayed_answer + "▌")
    time.sleep(0.01)

answer_placeholder.markdown(answer)
```

## 效果

用户看到的效果是回答按字逐步出现，类似大模型流式输出。

## 局限

这种方式不是后端真实流式。实际流程仍然是：

```text
前端等待后端完整生成回答
↓
后端一次性返回 answer
↓
前端按字显示 answer
```

所以它不能减少首字等待时间，只是改善显示效果。

## 后续升级

后续如果要做真正流式输出，可以改成：

```text
FastAPI StreamingResponse / SSE
+ LangChain agent.stream()
+ 前端逐块接收并显示
```
