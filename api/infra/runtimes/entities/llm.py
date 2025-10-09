from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


@dataclass
class LLMRequest:
    model: str
    messages: Iterable[Message]
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    tenant_id: str | None = None
    thread_id: UUID | None = None


@dataclass 
class LLMResponse:
    id: str
    content: str
    provider: str
    model: str
    usage: dict[str, int]
    cost: float = 0.0
