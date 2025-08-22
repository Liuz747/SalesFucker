import openai

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderConfig


class OpenAIProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = openai.AsyncOpenAI(api_key=config.api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        # Track request
        self.stats["requests"] += 1
        
        response = await self.client.chat.completions.create(
            model=request.model or "gpt-4o-mini",
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            provider="openai",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model)
        )

    def _calculate_cost(self, usage, model: str) -> float:
        # Simple cost calculation
        costs = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        }
        model_cost = costs.get(model, costs["gpt-4o-mini"])
        return (usage.prompt_tokens * model_cost["input"] / 1000 +
                usage.completion_tokens * model_cost["output"] / 1000)

