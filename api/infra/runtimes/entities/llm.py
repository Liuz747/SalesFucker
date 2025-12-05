from collections.abc import Mapping
from dataclasses import dataclass
from typing import Type
from uuid import UUID

from pydantic import BaseModel

from libs.types import MessageParams


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class LLMRequest:
    id: UUID | None
    model: str
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    thread_id: UUID | None = None
    output_model: Type[BaseModel] | None = None


@dataclass(kw_only=True)
class ResponseMessageRequest(LLMRequest):
    input: str
    system_prompt: str


@dataclass(kw_only=True)
class CompletionsRequest(LLMRequest):
    messages: MessageParams


@dataclass 
class LLMResponse:
    id: str
    content: str | Mapping
    provider: str
    model: str
    usage: TokenUsage
    cost: float = 0.0
