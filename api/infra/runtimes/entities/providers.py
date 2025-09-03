from enum import StrEnum

from typing import List, Optional
from dataclasses import dataclass
from .models import Model

class ProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"

@dataclass
class Provider:
    id: str
    type: ProviderType
    name: str
    api_key: str
    base_url: Optional[str] = None
    models: List[Model] = None
    enabled: bool = True
