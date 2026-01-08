"""
LLM 调用活动

封装与大模型交互的活动函数，用于生成各类自动化消息内容。
"""

from uuid import uuid4

from temporalio import activity

from infra.runtimes import (
    LLMClient,
    LLMResponse,
    CompletionsRequest,
    TokenUsage
)
from libs.types import MessageParams
from utils import get_component_logger

logger = get_component_logger(__name__)


@activity.defn
async def invoke_task_llm(
    model: str,
    provider: str,
    temperature: float,
    max_tokens: int,
    messages: MessageParams,
    fallback_prompt: str
) -> LLMResponse:
    """
    调用任务LLM活动

    Returns:
        LLMResponse: LLM 响应对象（包含生成的内容）
    """
    req_id = uuid4()
    try:
        llm_client = LLMClient()
        request = CompletionsRequest(
            id=req_id,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages
        )
        return await llm_client.completions(request)
    except Exception as e:
        logger.error(f"生成自动消息失败: {e}", exc_info=True)
        return LLMResponse(
            id=req_id,
            content=fallback_prompt,
            provider=provider,
            model=model,
            usage=TokenUsage(
                input_tokens=0,
                output_tokens=0
            )
        )