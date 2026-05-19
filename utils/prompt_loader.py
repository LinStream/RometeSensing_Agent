"""
Prompt 加载工具，参考原项目写法。
"""

from utils.config_handler import prompts_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


def load_rag_prompts() -> str:
    try:
        rag_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error("[load_rag_prompts] config/prompts.yml 中缺少 rag_summarize_prompt_path")
        raise e

    try:
        return open(rag_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[load_rag_prompts] 读取 RAG 提示词失败：{str(e)}")
        raise e


def load_agent_prompts() -> str:
    """
    加载 Agent system prompt。
    """
    try:
        agent_prompt_path = get_abs_path(prompts_conf["agent_system_prompt_path"])
    except KeyError as e:
        logger.error("[load_agent_prompts] config/prompts.yml 中缺少 agent_system_prompt_path")
        raise e

    try:
        return open(agent_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[load_agent_prompts] 读取 Agent 提示词失败：{str(e)}")
        raise e
