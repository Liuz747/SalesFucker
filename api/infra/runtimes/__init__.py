"""
LLM运行时模块

该模块提供轻量级的多LLM供应商支持，专为快速启动和测试设计。
相比复杂的src/llm系统，这个版本更简单、更直接。

核心组件:
- client.py: 统一LLM客户端
- config.py: 配置加载器
- routing.py: 简单路由器
- providers/: 供应商实现
- entities/: 数据模型
"""

from .client import LLMClient
from .config import LLMConfig
from .entities import (
    LLMRequest,
    LLMResponse,
    ProviderType,
    CompletionsRequest,
    ResponseMessageRequest,
    TokenUsage
)
from .routing import SimpleRouter
from .providers import OpenAIProvider, AnthropicProvider, BaseProvider

__all__ = [
    "CompletionsRequest",
    "ResponseMessageRequest",
    "LLMClient",
    "LLMConfig",
    "SimpleRouter",
    "OpenAIProvider",
    "AnthropicProvider",
    "BaseProvider",
    "LLMRequest",
    "LLMResponse",
    "ProviderType",
    "TokenUsage",
]