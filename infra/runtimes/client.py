"""
LLM客户端

统一的LLM客户端，支持多供应商智能路由和简单故障转移。
专为快速启动设计，无复杂功能。
"""

from typing import Dict

from infra.runtimes.providers import OpenAIProvider, AnthropicProvider, BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderType
from infra.runtimes.routing import SimpleRouter
from infra.runtimes.config import LLMConfig

class LLMClient:
    """统一LLM客户端"""

    def __init__(self, config: LLMConfig):
        """
        初始化LLM客户端
        
        参数:
            config: LLM配置对象
        """
        self.config = config
        self.providers: Dict[ProviderType, BaseProvider] = {}
        self.router = SimpleRouter(config.routing_config)
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化已启用的供应商"""
        if self.config.openai and self.config.openai.enabled:
            self.providers[ProviderType.OPENAI] = OpenAIProvider(self.config.openai)
        if self.config.anthropic and self.config.anthropic.enabled:
            self.providers[ProviderType.ANTHROPIC] = AnthropicProvider(self.config.anthropic)
        # 其他供应商可在此添加

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """
        主要聊天接口，带智能路由
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: LLM响应对象
        """
        try:
            # 路由到最佳供应商
            provider_type = self.router.route(request, list(self.providers.keys()))
            provider = self.providers[provider_type]

            # 发送请求
            response = await provider.chat(request)

            return response

        except Exception as e:
            # 简单故障转移
            return await self._handle_fallback(request, e)

    async def _handle_fallback(self, request: LLMRequest, error: Exception) -> LLMResponse:
        """
        简单故障转移逻辑
        
        参数:
            request: 原始请求
            error: 发生的错误
            
        返回:
            LLMResponse: 成功的响应
            
        异常:
            Exception: 所有供应商都失败时抛出
        """
        for provider_type, provider in self.providers.items():
            try:
                return await provider.chat(request)
            except Exception:
                continue
        raise Exception("All providers failed")

