"""
DashScope供应商实现

提供阿里云通义千问系列模型的调用功能。
"""

from typing import Any

import dashscope
from dashscope import AioGeneration, AioMultiModalConversation
from dashscope.api_entities.dashscope_response import GenerationResponse, MultiModalConversationResponse

from libs.types import MessageParams
from utils import get_component_logger
from .base import BaseProvider
from ..entities import (
    CompletionsRequest,
    LLMResponse,
    Provider,
    TokenUsage
)

logger = get_component_logger(__name__, "DashScopeProvider")


class DashScopeProvider(BaseProvider):
    """DashScope供应商实现类"""

    def __init__(self, provider: Provider):
        """
        初始化DashScope供应商

        Args:
            provider: DashScope配置
        """
        super().__init__(provider)
        dashscope.api_key = provider.api_key
        if provider.base_url:
            dashscope.base_http_api_url = provider.base_url

    def _format_message_content(self, content) -> str | list[dict[str, Any]]:
        """
        将通用content格式转换为DashScope特定格式

        Args:
            content: str（纯文本）或 Sequence[InputContent]（多模态）

        Returns:
            str 或 list[dict]: DashScope API所需格式
        """
        if isinstance(content, str):
            return content

        # 将InputContent序列转换为DashScope要求的字段
        formatted: list[dict[str, Any]] = []
        for item in content:
            if item.type == "text":
                formatted.append({"text": item.content})
            elif item.type == "input_image":
                formatted.append({"image": item.content})
        return formatted

    @staticmethod
    def _has_multimodal_input(messages: MessageParams) -> bool:
        """
        检测请求是否包含多模态内容

        Args:
            messages: 输入内容

        Returns:
            bool: 如果包含多模态内容返回True，否则返回False
        """
        for message in messages:
            if message.content and not isinstance(message.content, str):
                # content是Sequence[InputContent]类型，检查是否有非文本类型
                for item in message.content:
                    if item.type != "text":
                        return True
        return False

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到DashScope

        根据请求内容自动识别是否包含多模态输入，
        并路由到相应的API调用方法，然后统一处理响应。

        Args:
            request: LLM请求

        Returns:
            LLMResponse: DashScope响应
        """
        # 根据请求类型选择合适的API调用方法
        if self._has_multimodal_input(request.messages):
            logger.info("检测到多模态内容，使用多模态API")
            response = await self._call_multimodal_api(request)
        else:
            logger.info("纯文本请求，使用通用文本API")
            response = await self._call_text_api(request)

        # 统一处理响应
        if response.status_code != 200:
            error_msg = f"DashScope API错误: {response.code} - {response.message}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 提取消息内容
        message = response.output.choices[0].message
        content = message.content

        # 处理多模态响应中的列表格式内容
        if isinstance(content, list):
            # 提取第一个文本内容
            for item in content:
                if "text" in item:
                    content = item["text"]
                    break

        # 提取token使用情况
        token_usage = TokenUsage(
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0
        )

        return LLMResponse(
            id=request.id,
            content=content,
            provider=request.provider,
            model=request.model,
            usage=token_usage,
            finish_reason=response.output.choices[0].finish_reason
        )

    async def _call_text_api(self, request: CompletionsRequest) -> GenerationResponse:
        """
        调用DashScope纯文本API

        Args:
            request: LLM请求（仅包含文本内容）

        Returns:
            GenerationResponse: DashScope响应对象
        """
        # 构建消息列表
        messages = []
        for m in request.messages:
            message = {
                "role": m.role,
                "content": self._format_message_content(m.content) if m.content else ""
            }
            messages.append(message)

        try:
            return await AioGeneration.call(
                model=request.model,
                messages=messages,
                result_format='message',
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )

        except Exception as e:
            logger.error(f"DashScope文本API调用失败: {str(e)}")
            raise

    async def _call_multimodal_api(self, request: CompletionsRequest) -> MultiModalConversationResponse:
        """
        调用DashScope多模态API

        Args:
            request: LLM请求（包含图像、音频等多模态内容）

        Returns:
            MultiModalConversationResponse: DashScope响应对象
        """
        # 构建消息列表
        messages = []
        for m in request.messages:
            message = {
                "role": m.role,
                "content": self._format_message_content(m.content) if m.content else ""
            }
            messages.append(message)

        try:
            return await AioMultiModalConversation.call(
                model=request.model,
                messages=messages,
                result_format='message',
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )

        except Exception as e:
            logger.error(f"DashScope多模态API调用失败: {str(e)}")
            raise
