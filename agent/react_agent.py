"""
标准 LangChain Agent。

这一版采用单主线：
- 前端只调用 /api/chat/ask
- 后端统一进入 ReactAgent
- RAG 作为 Agent 的一个 tool

注意：
这里的 Agent 使用 LangChain create_agent，和你之前学习的 demo 思路一致。
"""

from langchain.agents import create_agent

from model.factory import chat_model
from utils.prompt_loader import load_agent_prompts


class ReactAgent:
    def __init__(self, tools):
        self.agent = create_agent(
            model=chat_model,
            tools=tools,
            system_prompt=load_agent_prompts(),
        )

    def invoke(self, question: str, history: str = "") -> str:
        """
        调用 Agent。

        history 会作为一条 system 消息放进去，让 Agent 理解连续追问。
        """
        messages = []

        if history:
            messages.append(
                {
                    "role": "system",
                    "content": f"以下是当前会话的历史对话，必要时用于理解用户追问：\n{history}",
                }
            )

        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        result = self.agent.invoke({"messages": messages})
        latest_message = result["messages"][-1]

        return getattr(latest_message, "content", str(latest_message))
