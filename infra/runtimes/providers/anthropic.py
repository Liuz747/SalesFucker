"""
Anthropic供应商实现

提供Anthropic Claude系列模型的调用功能。
支持Claude-3.5-Sonnet、Claude-3.5-Haiku等模型。
"""

import anthropic
from anthropic.types import MessageParam

from infra.runtimes.providers import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, Provider


class AnthropicProvider(BaseProvider):
    """Anthropic供应商实现类"""
    
    def __init__(self, provider: Provider):
        """
        初始化Anthropic供应商
        
        参数:
            config: Anthropic配置
        """
        super().__init__(provider)
        self.client = anthropic.AsyncAnthropic(api_key=provider.api_key)

    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        发送聊天请求到Anthropic
        
        参数:
            request: LLM请求
            
        返回:
            LLMResponse: Anthropic响应
        """
        # 构建包含历史记录的对话上下文
        full_context = self._build_conversation_context(request)
        messages: list[MessageParam] = full_context

        response = await self.client.messages.create(
            model=request.model or "claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=request.max_tokens or 4000,
            temperature=request.temperature
        )

        llm_response = LLMResponse(
            content=response.content[0].text,
            provider="anthropic",
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            cost=self._calculate_cost(response.usage, response.model),
            chat_id=request.chat_id
        )
        
        # 保存对话历史
        self._save_conversation_turn(request, llm_response)
        
        return llm_response

    def _calculate_cost(self, usage, model: str) -> float:
        """
        计算Anthropic请求成本
        
        参数:
            usage: 令牌使用情况
            model: 模型名称
            
        返回:
            float: 请求成本(美元)
        """
        # Anthropic简单成本计算
        costs = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125},
        }
        model_cost = costs.get(model, costs["claude-3-5-sonnet-20241022"])
        return (usage.input_tokens * model_cost["input"] / 1000 +
                usage.output_tokens * model_cost["output"] / 1000)
