"""
社交媒体公域导流服务

封装 LLM 调用、提示词拼装和结果解析逻辑，为控制器提供复用能力。
"""

from collections.abc import Mapping
from typing import Type
from uuid import uuid4

from pydantic import BaseModel

from infra.runtimes import LLMClient, ResponseMessageRequest
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTrafficService")


class SocialMediaServiceError(Exception):
    """社交媒体导流服务异常"""


class SocialMediaPublicTrafficService:
    """社交媒体引流文案生成服务"""

    client = LLMClient()

    @classmethod
    async def invoke_llm(
        cls,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[BaseModel]
    ) -> Mapping:
        """调用统一LLM客户端"""
        run_id = uuid4()
        request = ResponseMessageRequest(
            id=run_id,
            model="google/gemini-2.5-flash-preview-09-2025",
            provider="openrouter",
            temperature=0.5,
            max_tokens=4000,
            input=user_prompt,
            system_prompt=system_prompt,
            output_model=output_model
        )
        response = await cls.client.responses(request)
        return response.content
