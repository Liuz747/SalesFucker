import google.genai as genai

from ..entities import LLMRequest, LLMResponse, Provider
from .base import BaseProvider

class GeminiProvider(BaseProvider):
    def __init__(self, provider: Provider):
        super().__init__(provider)
        self.client = genai.Client(api_key=provider.api_key)

    async def completions(self, request: LLMRequest) -> LLMResponse:
        pass