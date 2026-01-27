"""
Anthropic供应商实现

提供Anthropic Claude系列模型的调用功能。
支持Claude-3.5-Sonnet、Claude-3.5-Haiku等模型。
"""

from typing import Any

import anthropic
from anthropic.types import MessageParam

from utils import get_component_logger
from .base import BaseProvider
from ..entities import CompletionsRequest, LLMResponse, Provider, TokenUsage

logger = get_component_logger(__name__, "AnthropicProvider")


class AnthropicProvider(BaseProvider):
    """Anthropic供应商实现类"""
    
    def __init__(self, provider: Provider):
        """
        初始化Anthropic供应商
        
        Args:
            provider: Anthropic配置
        """
        super().__init__(provider)
        self.client = anthropic.AsyncAnthropic(
            api_key=provider.api_key,
            base_url=provider.base_url
        )

    def _format_message_content(self, content) -> str | list[dict]:
        """
        将通用content格式转换为Anthropic特定格式

        Args:
            content: InputContentParams

        Returns:
            str 或 list[dict]: Anthropic API所需的content格式
        """
        if isinstance(content, str):
            return content

        # 将InputContent序列转换为Anthropic要求的字段
        formatted: list[dict[str, Any]] = []
        for item in content:
            if item.type == "text":
                formatted.append({"type": "text", "text": item.content})
            elif item.type == "input_image":
                formatted.append({
                    "type": "image",
                    "source": {"type": "url", "url": item.content}
                })
        return formatted

    def _format_messages(self, messages) -> list[MessageParam]:
        """
        将通用消息列表转换为Anthropic特定格式

        Args:
            messages: MessageParams（消息列表）

        Returns:
            list[MessageParam]: Anthropic API所需的消息格式
        """
        formatted_messages: list[MessageParam] = []
        for message in messages:
            if message.role != "tool" and message.role != "system" and message.content:
                formatted_content = self._format_message_content(message.content)
                formatted_message = MessageParam(role=message.role, content=formatted_content)
                formatted_messages.append(formatted_message)

        return formatted_messages

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到Anthropic

        Args:
            request: LLM请求

        Returns:
            LLMResponse: Anthropic响应
        """
        try:
            # 构建包含历史记录的对话上下文并处理多模态内容
            messages = self._format_messages(request.messages)

            response = await self.client.messages.create(
                model=request.model or "claude-3-5-sonnet-20241022",
                messages=messages,
                max_tokens=request.max_tokens or 4000,
                temperature=request.temperature
            )

            llm_response = LLMResponse(
                id=request.id,
                content=response.content[0].text,
                provider=request.provider,
                model=response.model,
                usage=TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                ),
                cost=self._calculate_cost(response.usage, response.model)
            )

            return llm_response

        except anthropic.APIError as e:
            logger.error(f"Anthropic API错误: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Anthropic completions调用失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _calculate_cost(usage, model: str) -> float:
        """
        计算Anthropic请求成本
        
        Args:
            usage: 令牌使用情况
            model: 模型名称
            
        Returns:
            float: 请求成本(美元)
        """
        # Anthropic简单成本计算
        costs = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125},
        }
        model_cost = costs.get(model, costs["claude-3-5-sonnet-20241022"])
        return (usage.input_tokens * model_cost["input"] / 1000 +
                usage.output_tokens * model_cost["output"] / 1000)
