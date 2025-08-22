from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class LLMRequest:
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tenant_id: Optional[str] = None

@dataclass 
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    cost: float = 0.0
