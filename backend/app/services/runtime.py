"""
运行时服务实例。

统一在这里创建 rag_service 和 agent。
这样 api/chat.py、api/documents.py 等模块都可以复用同一个服务实例，
避免接口层之间互相 import。
"""

from agent.react_agent import ReactAgent
from agent.tools import build_agent_tools
from rag.rag_service import RagSummarizeService

rag_service = RagSummarizeService()

agent_tools = build_agent_tools(rag_service)

react_agent = ReactAgent(tools=agent_tools)
