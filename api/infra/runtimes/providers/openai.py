"""
OpenAI供应商实现

提供OpenAI GPT系列模型的调用功能，支持函数调用（Function Calling）。
"""

import json

import openai
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam
)
from pydantic import ValidationError

from utils import get_component_logger
from .base import BaseProvider
from ..entities import (
    CompletionsRequest,
    LLMResponse,
    Provider,
    ResponseMessageRequest,
    TokenUsage,
    ToolCallData
)

logger = get_component_logger(__name__, "OpenAIProvider")


class OpenAIProvider(BaseProvider):
    """OpenAI供应商实现类"""

    def __init__(self, provider: Provider):
        """
        初始化OpenAI供应商

        Args:
            provider: OpenAI配置
        """
        super().__init__(provider)
        self.client = openai.AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url
        )

    def _format_message_content(self, content) -> str | list[ChatCompletionContentPartParam]:
        """
        将通用content格式转换为OpenAI特定格式

        Args:
            content: str（纯文本）或 Sequence[InputContent]（多模态）

        Returns:
            str 或 list[ChatCompletionContentPartParam]: OpenAI API所需的content格式
        """
        if isinstance(content, str):
            return content

        # 将InputContent序列转换为OpenAI要求的字段
        formatted: list[ChatCompletionContentPartParam] = []
        for item in content:
            match item.type:
                case "text":
                    text_part: ChatCompletionContentPartTextParam = {
                        "type": "text",
                        "text": item.content
                    }
                    formatted.append(text_part)
                case "input_image":
                    image_part: ChatCompletionContentPartImageParam = {
                        "type": "image_url",
                        "image_url": {"url": item.content}
                    }
                    formatted.append(image_part)
        return formatted

    def _format_messages(self, messages) -> list[ChatCompletionMessageParam]:
        """
        将通用消息列表转换为OpenAI特定格式

        Args:
            messages: MessageParams（消息列表）

        Returns:
            list[ChatCompletionMessageParam]: OpenAI API所需的消息格式
        """
        formatted_messages: list[ChatCompletionMessageParam] = []
        for m in messages:
            match m.role:
                case "user":
                    user_msg: ChatCompletionUserMessageParam = {
                        "role": "user",
                        "content": self._format_message_content(m.content)
                    }
                    formatted_messages.append(user_msg)

                case "assistant":
                    assistant_msg: ChatCompletionAssistantMessageParam = {
                        "role": "assistant",
                        "content": self._format_message_content(m.content) if m.content else None
                    }
                    if getattr(m, "tool_calls", None):
                        assistant_msg["tool_calls"] = m.tool_calls
                    formatted_messages.append(assistant_msg)

                case _:
                    formatted_messages.append(m.model_dump())

        return formatted_messages

    @staticmethod
    def _parse_tool_calls(message) -> list[ToolCallData] | None:
        """
        解析 OpenAI 响应中的工具调用

        Args:
            message: OpenAI ChatCompletionMessage

        Returns:
            list[ToolCallData] | None: 解析后的工具调用列表
        """
        if not message.tool_calls:
            return None

        tool_calls = []
        for tc in message.tool_calls:
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                logger.warning(f"工具调用参数解析失败: {tc.function.arguments}")
                arguments = {}

            tool_calls.append(ToolCallData(
                id=tc.id,
                name=tc.function.name,
                arguments=arguments
            ))

        return tool_calls

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到OpenAI

        Args:
            request: LLM请求

        Returns:
            LLMResponse: OpenAI响应
        """
        # 构建包含历史记录的对话上下文并处理多模态内容
        messages = self._format_messages(request.messages)

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens,
            tools=[tool.to_openai_tool() for tool in request.tools] if request.tools else None,
            tool_choice=request.tool_choice if request.tool_choice else None
        )

        message = response.choices[0].message
        tool_calls = self._parse_tool_calls(message)

        llm_response = LLMResponse(
            id=request.id,
            content=message.content,
            provider=request.provider,
            model=response.model,
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
            cost=self._calculate_cost(response.usage, response.model),
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason
        )

        return llm_response

    async def completions_structured(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送结构化聊天请求到OpenAI或OpenRouter

        Args:
            request: LLM请求

        Returns:
            LLMResponse: OpenAI响应
        """
        # 构建包含历史记录的对话上下文并处理多模态内容
        messages = self._format_messages(request.messages)

        # 为OpenRouter使用JSON schema格式，为原生OpenAI使用.parse()
        if request.provider == "openrouter" and not request.model.startswith("openai/"):
            # OpenRouter方式：使用json_object模式（json_schema在OpenRouter上不可靠）
            # 在系统消息中添加JSON格式要求
            json_schema_str = json.dumps(request.output_model.model_json_schema(), indent=2, ensure_ascii=False)

            # 在最后一条用户消息后添加JSON格式指令
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += f"\n\n请严格按照以下JSON schema格式返回结果，只返回JSON对象，不要包含任何其他文字、解释或markdown格式：\n\n{json_schema_str}\n\n只返回符合schema的纯JSON对象。"

            response = await self.client.chat.completions.create(
                extra_body={"provider": {'require_parameters': True}},
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_completion_tokens=request.max_tokens,
                response_format={
                    "type": "json_object",
                    "json_schema": request.output_model.model_json_schema()
                }
            )

            # 解析JSON响应
            content_str = response.choices[0].message.content.strip()

            try:
                # 解析JSON并验证
                parsed_data = json.loads(content_str)
                parsed_content = request.output_model.model_validate(parsed_data)
                logger.info(f"成功解析OpenRouter响应为 {request.output_model.__name__}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败。内容长度: {len(content_str)}, 前200字符: {content_str[:200]}")
                raise ValueError(f"LLM返回的不是有效的JSON: {e}. 内容: {content_str[:200]}")
            except ValidationError as e:
                logger.error(f"Pydantic验证失败。")
                raise ValueError(f"LLM返回的JSON不符合预期格式: {e}")
        else:
            # 原生OpenAI方式：使用.parse()
            response = await self.client.chat.completions.parse(
                response_format=request.output_model,
                model=request.model or "gpt-4o-mini",
                messages=messages,
                temperature=request.temperature,
                max_completion_tokens=request.max_tokens
            )
            parsed_content = response.choices[0].message.parsed
            if not parsed_content:
                raise ValueError("LLM返回了空的parsed响应")

        llm_response = LLMResponse(
            id=request.id,
            content=parsed_content,
            provider=request.provider,
            model=response.model,
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            ),
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
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            # cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response

    async def responses_structured(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        使用OpenAI Responses API的Structured Outputs功能获取结构化输出

        Structured Outputs确保模型输出严格遵循指定的JSON Schema,
        通过Pydantic模型定义输出结构,实现类型安全和数据验证。
        适用于需要可靠结构化数据的场景,如数据提取、表单填充等。

        Args:
            request: ResponseMessageRequest请求对象,必须包含output_model (Pydantic BaseModel类型)

        Returns:
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
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            # cost=self._calculate_cost(response.usage, response.model)
        )

        return llm_response


    @staticmethod
    def _calculate_cost(usage, model: str) -> float:
        """
        计算OpenAI请求成本

        Args:
            usage: 令牌使用情况
            model: 模型名称

        Returns:
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
