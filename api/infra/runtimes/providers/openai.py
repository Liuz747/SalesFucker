"""
OpenAI供应商实现

提供OpenAI GPT系列模型的调用功能。
支持GPT-4o、GPT-4o-mini等模型。
"""

import re
from typing import Any

import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionContentPartParam

from ..entities import LLMResponse, Provider, CompletionsRequest, ResponseMessageRequest
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI供应商实现类"""

    def __init__(self, provider: Provider):
        """
        初始化OpenAI供应商

        参数:
            provider: OpenAI配置
        """
        super().__init__(provider)
        self.client = openai.AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url
        )

    def _format_message_content(self, content) -> Any:
        """
        将通用content格式转换为OpenAI特定格式

        参数:
            content: str（纯文本）或 Sequence[InputContent]（多模态）

        返回:
            str 或 list[dict]: OpenAI API所需格式
        """
        if isinstance(content, str):
            return content

        # 将InputContent序列转换为OpenAI要求的字段
        formatted: list[ChatCompletionContentPartParam] = []
        for item in content:
            if item.type == "text":
                formatted.append({"type": "text", "text": item.content})
            elif item.type == "input_image":
                formatted.append({
                    "type": "image_url",
                    "image_url": {"url": item.content}
                })
        return formatted

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到OpenAI

        参数:
            request: LLM请求

        返回:
            LLMResponse: OpenAI响应
        """
        # 构建包含历史记录的对话上下文并处理多模态内容
        messages: list[ChatCompletionMessageParam] = []
        for message in request.messages:
            messages.append({
                "role": message.role,
                "content": self._format_message_content(message.content)
            })

        response = await self.client.chat.completions.create(
            model=request.model or "gpt-4o-mini",
            messages=messages,
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens
        )

        llm_response = LLMResponse(
            id=request.id,
            content=response.choices[0].message.content,
            provider=request.provider,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response

    async def completions_structured(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到OpenAI

        参数:
            request: LLM请求

        返回:
            LLMResponse: OpenAI响应
        """
        # 构建包含历史记录的对话上下文并处理多模态内容
        messages: list[ChatCompletionMessageParam] = []
        for message in request.messages:
            messages.append({
                "role": message.role,
                "content": self._format_message_content(message.content)
            })

        response = await self.client.chat.completions.parse(
            response_format=request.output_model,
            model=request.model or "gpt-4o-mini",
            messages=messages,
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens
        )

        llm_response = LLMResponse(
            id=request.id,
            content=response.choices[0].message.parsed,
            provider=request.provider,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response
    async def responses(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        调用OpenAI Responses API获取回复内容。
        """

        response = await self.client.responses.create(
            input=request.input,
            instructions=request.system_prompt,
            max_output_tokens=request.max_tokens,
            model=request.model,
            temperature=request.temperature,
            store=False
        )

        llm_response = LLMResponse(
            id=request.id,
            content=response.output_text,
            provider=request.provider,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            # cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response

    async def responses_structured(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        使用OpenAI Responses API的Structured Outputs功能获取结构化输出

        Structured Outputs确保模型输出严格遵循指定的JSON Schema,
        通过Pydantic模型定义输出结构,实现类型安全和数据验证。
        适用于需要可靠结构化数据的场景,如数据提取、表单填充等。

        参数:
            request: ResponseMessageRequest请求对象,必须包含output_model (Pydantic BaseModel类型)

        返回:
            LLMResponse: 统一的LLM响应对象,content字段包含解析后的Pydantic对象
        """

        response = await self.client.responses.parse(
            text_format=request.output_model,
            input=request.input,
            instructions=request.system_prompt,
            max_output_tokens=request.max_tokens,
            model=request.model,
            temperature=request.temperature,
            store=False
        )

        llm_response = LLMResponse(
            id=request.id,
            content=response.output_parsed,
            provider=request.provider,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            # cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response


    def _calculate_cost(self, usage, model: str) -> float:
        """
        计算OpenAI请求成本

        参数:
            usage: 令牌使用情况
            model: 模型名称

        返回:
            float: 请求成本(美元)
        """
        # 简单成本计算
        costs = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        }
        model_cost = costs.get(model, costs["gpt-4o-mini"])
        return (usage.prompt_tokens * model_cost["input"] / 1000 +
                usage.completion_tokens * model_cost["output"] / 1000)
