"""
LLM客户端

统一的LLM客户端，支持多供应商智能路由和简单故障转移。
专为快速启动设计，无复杂功能。
"""

from typing import Dict

from infra.runtimes.providers import OpenAIProvider, AnthropicProvider, OpenRouterProvider, BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse, ProviderType
# from infra.runtimes.routing import SimpleRouter
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
        self.active_providers: Dict[str, BaseProvider] = {}
        # self.router = SimpleRouter(config.routing_config)
        self._dispatch()

    def _dispatch(self):
        """初始化已启用的供应商"""
        for provider in self.config.providers:
            if provider.enabled:
                if provider.type == ProviderType.OPENAI:
                    self.active_providers[provider.id] = OpenAIProvider(provider)
                elif provider.type == ProviderType.ANTHROPIC:
                    self.active_providers[provider.id] = AnthropicProvider(provider)
                elif provider.type == ProviderType.GEMINI:
                    pass
                elif provider.type == ProviderType.OPENROUTER:
                    self.active_providers[provider.id] = OpenRouterProvider(provider)
                else:
                    raise Exception(f"不支持的供应商类型: {provider.type}")

    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        主要聊天接口，支持显式和智能路由
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: LLM响应对象
        """
        try:
            # 直接使用ProviderID
            provider_id = request.provider.lower()
            if provider_id not in self.active_providers:
                raise Exception(f"指定的供应商不可用: {request.provider}")
            
            provider = self.active_providers[provider_id]
            
            # 发送请求
            response = await provider.completions(request)
            return response

        except ValueError:
            raise Exception(f"无效的供应商: {request.provider}")
        except Exception as e:
            raise e


