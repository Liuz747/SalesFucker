from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Type
from uuid import UUID

from pydantic import BaseModel

from libs.types import MessageParams, ToolDefinition


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class ToolCallData:
    """LLM 返回的工具调用数据"""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMRequest:
    id: UUID | None
    model: str
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    output_model: Type[BaseModel] | None = None


@dataclass
class LLMResponse:
    id: UUID | None
    content: str | Mapping | None
    provider: str
    model: str
    usage: TokenUsage
    cost: float = 0.0
    tool_calls: list[ToolCallData] | None = None
    finish_reason: str | None = None


@dataclass(kw_only=True)
class CompletionsRequest(LLMRequest):
    messages: MessageParams
    tools: list[ToolDefinition] | None = None
    tool_choice: Literal["auto", "required", "none"] | None = None


@dataclass(kw_only=True)
class ResponseMessageRequest(LLMRequest):
    input: str
    system_prompt: str
