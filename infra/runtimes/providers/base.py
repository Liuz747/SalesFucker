from abc import ABC, abstractmethod
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderConfig

class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.stats = {"requests": 0}

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        pass

