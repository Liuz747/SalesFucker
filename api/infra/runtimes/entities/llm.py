from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str | Sequence[Mapping[str, Any]]


@dataclass
class LLMRequest:
    id: UUID | None
    model: str
    messages: Iterable[Message]
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    thread_id: UUID | None = None


@dataclass 
class LLMResponse:
    id: str
    content: str
    provider: str
    model: str
    usage: dict[str, int]
    cost: float = 0.0
