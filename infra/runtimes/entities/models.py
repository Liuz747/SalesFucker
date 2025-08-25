from enum import StrEnum
from typing import Optional, List
from dataclasses import dataclass


class ModelType(StrEnum):
    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    REASONING = "reasoning"
    FUNCTION_CALLING = "function_calling"


@dataclass
class Model:
    id: str
    provider: str
    name: str
    type: Optional[ModelType]
    enabled: bool = True