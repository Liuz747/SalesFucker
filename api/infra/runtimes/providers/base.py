"""
LLM供应商基类

定义所有LLM供应商的统一接口。
所有具体供应商实现都必须继承此基类。
"""

from abc import ABC, abstractmethod

from infra.runtimes.entities import LLMRequest, LLMResponse, Provider

class BaseProvider(ABC):
    """LLM供应商抽象基类"""

    def __init__(self, provider: Provider):
        """
        初始化供应商

        参数:
            provider: 供应商配置
        """
        self.provider = provider

    @abstractmethod
    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        发送聊天请求 (抽象方法)
        
        参数:
            request: LLM请求
            
        返回:
            LLMResponse: LLM响应
        """
        pass
