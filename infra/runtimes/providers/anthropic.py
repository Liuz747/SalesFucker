import anthropic
import google.genai as genai

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderConfig


class AnthropicProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        # Track request
        self.stats["requests"] += 1
        
        # Convert OpenAI format to Anthropic format
        messages = self._convert_messages(request.messages)

        response = await self.client.messages.create(
            model=request.model or "claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=request.max_tokens or 4000,
            temperature=request.temperature
        )

        return LLMResponse(
            content=response.content[0].text,
            provider="anthropic",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model)
        )

    def _convert_messages(self, messages):
        """Convert OpenAI format to Anthropic format"""
        # Anthropic doesn't use system messages in the same way
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                # Skip system messages or convert to user message
                continue
            converted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return converted

    def _calculate_cost(self, usage, model: str) -> float:
        """Calculate cost for Anthropic"""
        # Simple cost calculation for Anthropic
        costs = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125},
        }
        model_cost = costs.get(model, costs["claude-3-5-sonnet-20241022"])
        return (usage.input_tokens * model_cost["input"] / 1000 +
                usage.output_tokens * model_cost["output"] / 1000)
