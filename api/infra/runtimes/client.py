"""
LLM客户端

统一的LLM客户端，支持多供应商智能路由和简单故障转移。
专为快速启动设计，无复杂功能。
"""

# from infra.runtimes.routing import SimpleRouter
from utils import get_component_logger
from .config import LLMConfig
from .entities import LLMResponse, ProviderType, CompletionsRequest, ResponseMessageRequest
from .providers import AnthropicProvider, BaseProvider, OpenAIProvider

logger = get_component_logger(__name__, "LLMClient")

config = LLMConfig()


class LLMClient:
    """统一LLM客户端"""

    def __init__(self):
        """
        初始化LLM客户端
        
        参数:
            config: LLM配置对象
        """
        self.config = config
        self.active_providers: dict[str, BaseProvider] = {}
        # self.router = SimpleRouter(config.routing_config)
        self._dispatch_providers()

    def _dispatch_providers(self):
        """初始化已启用的供应商"""
        for provider in self.config.providers:
            if provider.enabled:
                if provider.type == ProviderType.OPENAI:
                    self.active_providers[provider.id] = OpenAIProvider(provider)
                elif provider.type == ProviderType.ANTHROPIC:
                    self.active_providers[provider.id] = AnthropicProvider(provider)
                elif provider.type == ProviderType.GEMINI:
                    pass
                else:
                    raise Exception(f"不支持的供应商类型: {provider.type}")

    def _get_provider(self, provider_id: str, model_id: str) -> BaseProvider:
        """
        获取并验证供应商

        参数:
            provider_id: 供应商ID

        返回:
            BaseProvider: 供应商实例
        """
        provider_id = provider_id.lower()

        if provider_id not in self.active_providers:
            raise ValueError(f"指定的供应商不可用: {provider_id}")

        provider = self.active_providers[provider_id]

        return provider

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        主要聊天接口

        参数:
            request: LLM请求对象

        返回:
            LLMResponse: LLM响应对象
        """
        provider = self._get_provider(request.provider, request.model)

        try:
            if request.output_model:
                return await provider.completions_structured(request)
            else:
                return await provider.completions(request)
        except NotImplementedError:
            raise
        except Exception as e:
            logger.error(f"供应商 {request.provider} 调用失败: {str(e)}")
            raise

    async def responses(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        使用Responses API处理单轮对话请求

        Responses API相比Chat Completions更简洁,
        适合单轮对话场景。支持更好的推理性能和内置工具。

        参数:
            request: ResponseMessageRequest请求对象

        返回:
            LLMResponse: 统一的LLM响应对象

        异常:
            ValueError: 当供应商不可用时
            NotImplementedError: 当供应商不支持 Responses API 时
        """
        provider = self._get_provider(request.provider, request.model)

        try:
            if request.output_model:
                return await provider.responses_structured(request)
            else:
                return await provider.responses(request)
        except NotImplementedError:
            raise
        except Exception as e:
            logger.error(f"供应商 {request.provider} 调用失败: {str(e)}")
            raise
