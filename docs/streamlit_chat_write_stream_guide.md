# Streamlit 聊天式伪流式输出说明

本项目的前端现在使用 `st.chat_input()`、`st.chat_message()` 和 `st.write_stream()` 实现聊天式页面。

## 为什么是伪流式

当前后端 `/api/chat/ask` 仍然是普通 HTTP 接口：

```text
前端请求后端
↓
后端 Agent 完整生成 answer
↓
一次性返回 JSON
↓
前端拿到完整 answer 后逐字展示
```

所以这不是真正的后端流式，只是前端用 `write_stream()` 模拟逐字输出。

## 核心代码

```python
def fake_stream(text: str):
    for char in text:
        time.sleep(0.01)
        yield char

streamed_answer = st.write_stream(fake_stream(answer))
```

含义：

```text
1. fake_stream 是一个生成器
2. 每次 yield 一个字符
3. write_stream 接收生成器，并逐步把字符写到页面
4. write_stream 返回最终完整字符串
5. 把完整字符串保存到 st.session_state.messages
```

## 为什么不用 st.empty()

`st.empty()` 也可以实现逐字刷新，但它更像手动刷新占位符。

`st.write_stream()` 是 Streamlit 为聊天/流式输出提供的更自然写法，和 `st.chat_message()` 搭配更清晰。

## 真正流式以后怎么做

真正流式需要后端也支持流式，例如：

```text
FastAPI StreamingResponse / SSE
+
LangChain agent.stream()
+
前端逐块读取响应
```

当前阶段先用前端伪流式，改动小、稳定，不破坏现有 FastAPI + Agent 主线。
