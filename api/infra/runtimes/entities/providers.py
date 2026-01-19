from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from .models import Model

class ProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DASHSCOPE = "dashscope"
    OPENROUTER = "openrouter"


@dataclass
class Provider:
    id: str
    type: ProviderType
    name: str
    api_key: str
    base_url: Optional[str] = None
    models: list[Model] = None
