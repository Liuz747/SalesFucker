"""
OpenAI供应商实现

提供OpenAI GPT系列模型的调用功能。
支持GPT-4o、GPT-4o-mini等模型。
"""

import openai
from openai.types.chat import ChatCompletionMessageParam

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, Provider


class OpenAIProvider(BaseProvider):
    """OpenAI供应商实现类"""
    
    def __init__(self, provider: Provider):
        """
        初始化OpenAI供应商
        
        参数:
            provider: OpenAI配置
        """
        super().__init__(provider)
        self.client = openai.AsyncOpenAI(api_key=provider.api_key)

    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        发送聊天请求到OpenAI
        
        参数:
            request: LLM请求
            
        返回:
            LLMResponse: OpenAI响应
        """
        # 构建包含历史记录的对话上下文
        full_context = self._build_conversation_context(request)
        messages: list[ChatCompletionMessageParam] = full_context
        
        response = await self.client.chat.completions.create(
            model=request.model or "gpt-4o-mini",
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        llm_response = LLMResponse(
            content=response.choices[0].message.content,
            provider="openai",
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model),
            chat_id=request.chat_id
        )
        
        # 保存对话历史
        self._save_conversation_turn(request, llm_response)
        
        return llm_response

    def _calculate_cost(self, usage, model: str) -> float:
        """
        计算OpenAI请求成本
        
        参数:
            usage: 令牌使用情况
            model: 模型名称
            
        返回:
            float: 请求成本(美元)
        """
        # 简单成本计算
        costs = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        }
        model_cost = costs.get(model, costs["gpt-4o-mini"])
        return (usage.prompt_tokens * model_cost["input"] / 1000 +
                usage.completion_tokens * model_cost["output"] / 1000)

