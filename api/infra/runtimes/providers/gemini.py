import google.genai as genai

from .base import BaseProvider
from ..entities import LLMRequest, LLMResponse, Provider

class GeminiProvider(BaseProvider):
    def __init__(self, provider: Provider):
        super().__init__(provider)
        self.client = genai.Client(api_key=provider.api_key)

    async def completions(self, request: LLMRequest) -> LLMResponse:
        pass