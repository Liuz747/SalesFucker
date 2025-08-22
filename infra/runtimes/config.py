import os
from typing import Optional, Dict, Any

from infra.runtimes.entities import ProviderConfig

class LLMConfig:

    def __init__(self):
        self.openai = self._load_openai_config()
        self.anthropic = self._load_anthropic_config()
        # self.gemini = self._load_gemini_config()
        # self.deepseek = self._load_deepseek_config()
        self.routing_config = self._load_routing_config()

    def _load_openai_config(self) -> Optional[ProviderConfig]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        return ProviderConfig(
            api_key=api_key,
            models=["gpt-4o", "gpt-4o-mini"],
            enabled=True
        )

    def _load_anthropic_config(self) -> Optional[ProviderConfig]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        return ProviderConfig(
            api_key=api_key,
            models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            enabled=True
        )

    # Similar for other providers...

    def _load_routing_config(self) -> Dict[str, Any]:
        return {
            "default_provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
            "fallback_provider": os.getenv("FALLBACK_LLM_PROVIDER", "anthropic"),
            "enable_chinese_routing": True,
            "enable_vision_routing": True
        }
