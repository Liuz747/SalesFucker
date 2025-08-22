from typing import Dict, Any

from infra.runtimes.providers import OpenAIProvider, AnthropicProvider, BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderType
from infra.runtimes.routing import SimpleRouter
from infra.runtimes.config import LLMConfig

class LLMClient:
    """Simplified unified LLM client"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.providers: Dict[ProviderType, BaseProvider] = {}
        self.router = SimpleRouter(config.routing_config)
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize enabled providers"""
        if self.config.openai and self.config.openai.enabled:
            self.providers[ProviderType.OPENAI] = OpenAIProvider(self.config.openai)
        if self.config.anthropic and self.config.anthropic.enabled:
            self.providers[ProviderType.ANTHROPIC] = AnthropicProvider(self.config.anthropic)
        # etc.

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Main chat interface with intelligent routing"""
        try:
            # Route to best provider
            provider_type = self.router.route(request, list(self.providers.keys()))
            provider = self.providers[provider_type]

            # Make request
            response = await provider.chat(request)

            # Update routing stats
            self.router.record_success(provider_type, response)
            return response

        except Exception as e:
            # Simple fallback
            return await self._handle_fallback(request, e)

    async def _handle_fallback(self, request: LLMRequest, error: Exception) -> LLMResponse:
        """Simple fallback logic"""
        for provider_type, provider in self.providers.items():
            try:
                return await provider.chat(request)
            except Exception:
                continue
        raise Exception("All providers failed")

    def get_stats(self) -> Dict[str, Any]:
        """Simple stats"""
        return {
            "available_providers": list(self.providers.keys()),
            "routing_stats": self.router.get_stats(),
            "total_requests": sum(p.stats.get("requests", 0) for p in self.providers.values())
        }
