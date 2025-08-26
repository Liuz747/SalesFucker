from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class LLMRequest:
    id: Optional[str]
    messages: List[Dict[str, str]]
    model: str
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tenant_id: Optional[str] = None

@dataclass 
class LLMResponse:
    id: str
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    cost: float = 0.0