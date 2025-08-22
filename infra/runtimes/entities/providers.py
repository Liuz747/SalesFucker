from enum import StrEnum

from typing import List, Optional
from dataclasses import dataclass

class ProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"

@dataclass
class ProviderConfig:
    api_key: str
    base_url: Optional[str] = None
    models: List[str] = None
    enabled: bool = True
