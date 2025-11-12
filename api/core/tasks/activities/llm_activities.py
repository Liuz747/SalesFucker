"""
LLM 调用活动

封装与大模型交互的活动函数，用于生成各类自动化消息内容。
"""

from uuid import UUID

from temporalio import activity

from core.prompts.template_loader import get_prompt_template
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__)


@activity.defn
async def invoke_task_llm(thread_id: UUID, task_name: str):
    """
    调用任务LLM活动
    """
    try:
        llm_client = LLMClient()

        prompt = get_prompt_template(task_name)

        if not prompt:
            raise ValueError(f"Template not found for task: {task_name}")

        request = CompletionsRequest(
            id=None,
            model="gpt-4o-mini",
            provider='openai',
            max_tokens=1024,
            thread_id=thread_id,
            messages=[Message(role='user', content=prompt)]
        )

        response = await llm_client.completions(request)
        return response.content
    except Exception as e:
        logger.error(f"生成自动消息失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
        return "您好！我是您的专属助手，有什么可以帮助您的吗？"