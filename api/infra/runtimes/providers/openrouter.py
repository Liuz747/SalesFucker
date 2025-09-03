"""
OpenRouter供应商实现

通过OpenRouter平台提供多个LLM供应商的统一访问接口。
支持GPT、Claude、Gemini等多种模型。
"""

import openai
from openai.types.chat import ChatCompletionMessageParam

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, Provider


class OpenRouterProvider(BaseProvider):
    """OpenRouter供应商实现类"""

    def __init__(self, provider: Provider):
        """
        初始化OpenRouter供应商

        参数:
            provider: OpenRouter配置
        """
        super().__init__(provider)
        # OpenRouter兼容OpenAI API格式
        self.client = openai.AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url or "https://openrouter.ai/api/v1"
        )

    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        发送聊天请求到OpenRouter

        参数:
            request: LLM请求

        返回:
            LLMResponse: OpenRouter响应
        """
        # 构建包含历史记录的对话上下文
        full_context = self._build_conversation_context(request)
        messages: list[ChatCompletionMessageParam] = full_context

        model = request.model or "openai/gpt-5-chat"

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        llm_response = LLMResponse(
            content=response.choices[0].message.content,
            provider="openrouter",
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model),
            id=request.id
        )

        # 保存对话历史
        self._save_conversation_turn(request, llm_response)

        return llm_response

    def _calculate_cost(self, usage, model: str) -> float:
        """
        计算OpenRouter请求成本

        参数:
            usage: 令牌使用情况
            model: 模型名称

        返回:
            float: 请求成本(美元)
        """
        # OpenRouter GPT-5系列模型定价（每1000个token的价格，美元）
        # 根据OpenRouter官方定价：https://openrouter.ai/openai/gpt-5-chat 和 https://openrouter.ai/openai/gpt-5-mini
        costs = {
            "openai/gpt-5-chat": {"input": 1.25, "output": 10.0},      # $1.25/M input, $10/M output
            "openai/gpt-5-mini": {"input": 0.25, "output": 2.0},       # $0.25/M input, $2/M output
        }

        # 默认使用GPT-5 Mini的定价
        model_cost = costs.get(model, costs["openai/gpt-5-mini"])
        return (usage.prompt_tokens * model_cost["input"] / 1000 +
                usage.completion_tokens * model_cost["output"] / 1000)