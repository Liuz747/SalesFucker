import google.genai as genai

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderConfig

class GeminiProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = genai.Client(api_key=config.api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        pass