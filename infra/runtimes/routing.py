from typing import List, Dict, Any
from infra.runtimes.entities import ProviderType, LLMRequest, LLMResponse

class SimpleRouter:
    """Dead simple routing - no over-engineering"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats: Dict[ProviderType, Dict[str, Any]] = {}

        # Simple rules
        self.chinese_providers = [ProviderType.DEEPSEEK, ProviderType.OPENAI]
        self.vision_providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]

    def route(self, request: LLMRequest, available_providers: List[ProviderType]) -> ProviderType:
        """Simple routing logic"""

        # Rule 0: Model-based routing (highest priority)
        if request.model:
            if "claude" in request.model.lower() and ProviderType.ANTHROPIC in available_providers:
                return ProviderType.ANTHROPIC
            elif "gpt" in request.model.lower() and ProviderType.OPENAI in available_providers:
                return ProviderType.OPENAI

        # Rule 1: Chinese content -> prefer DeepSeek/OpenAI
        if self._is_chinese_content(request):
            for provider in self.chinese_providers:
                if provider in available_providers:
                    return provider

        # Rule 2: Vision content -> OpenAI/Anthropic
        if self._has_vision_content(request):
            for provider in self.vision_providers:
                if provider in available_providers:
                    return provider

        # Rule 3: Default to first available
        return available_providers[0] if available_providers else ProviderType.OPENAI

    def _is_chinese_content(self, request: LLMRequest) -> bool:
        """Simple Chinese detection"""
        text = " ".join([msg.get("content", "") for msg in request.messages])
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def _has_vision_content(self, request: LLMRequest) -> bool:
        """Check for image content"""
        for msg in request.messages:
            if isinstance(msg.get("content"), list):
                return True
        return False

    def record_success(self, provider: ProviderType, response: LLMResponse):
        """Record success for simple stats"""
        if provider not in self.stats:
            self.stats[provider] = {"requests": 0, "total_cost": 0}

        self.stats[provider]["requests"] += 1
        self.stats[provider]["total_cost"] += response.cost

    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)

