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
        self._init()

    def _init(self):
        """初始化已启用的供应商"""
        if self.config.openai and self.config.openai.enabled:
            self.providers[ProviderType.OPENAI] = OpenAIProvider(self.config.openai)
        if self.config.anthropic and self.config.anthropic.enabled:
            self.providers[ProviderType.ANTHROPIC] = AnthropicProvider(self.config.anthropic)
        # 其他供应商可在此添加

    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        主要聊天接口，支持显式和智能路由
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: LLM响应对象
        """
        try:
            # 直接使用ProviderType枚举
            provider_type = ProviderType(request.provider.lower())
            if provider_type not in self.providers:
                raise Exception(f"指定的供应商不可用: {request.provider}")
            
            provider = self.providers[provider_type]
            
            # 发送请求
            response = await provider.completions(request)
            return response

        except ValueError:
            raise Exception(f"无效的供应商: {request.provider}")
        except Exception as e:
            raise e


