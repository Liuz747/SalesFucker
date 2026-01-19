"""
LLM供应商基类

定义所有LLM供应商的统一接口。
所有具体供应商实现都必须继承此基类。
"""

from abc import ABC, abstractmethod

from libs.types import InputContentParams
from ..entities import (
    CompletionsRequest,
    LLMResponse,
    Provider,
    ResponseMessageRequest,
)

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
    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求 (抽象方法)

        参数:
            request: LLM请求

        返回:
            LLMResponse: LLM响应
        """
        pass

    async def completions_structured(self, request: CompletionsRequest) -> LLMResponse:
        """
        结构化输出支持

        参数:
            request: LLM请求对象，必须包含output_model

        返回:
            LLMResponse: LLM响应，content字段包含解析后的结构化对象
        """
        raise NotImplementedError(f"{request.provider} 不支持结构化输出。")

    @abstractmethod
    def _format_message_content(self, content: InputContentParams):
        """
        将通用content格式转换为供应商特定格式 (抽象方法)

        参数:
            content: str（纯文本）或 Sequence[InputContent]（多模态）

        返回:
            任意类型: 供应商所需的content格式表示
        """
        pass

    async def responses(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        可选的 Responses API 支持

        参数:
            request: ResponseMessageRequest请求对象

        返回:
            LLMResponse: LLM响应
        """
        raise NotImplementedError(f"{request.provider} 不支持 Responses API。")

    async def responses_structured(self, request: ResponseMessageRequest) -> LLMResponse:
        """
        可选的 Responses API 结构化输出支持

        参数:
            request: ResponseMessageRequest请求对象，必须包含output_model

        返回:
            LLMResponse: LLM响应，content字段包含解析后的结构化对象
        """
        raise NotImplementedError(f"{request.provider} 不支持 Responses API 的结构化输出。")
