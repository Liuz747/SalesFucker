"""
LLM 提供商配置模块

包含所有 LLM 提供商配置，包括 API 密钥和多LLM 设置。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """
    LLM 提供商和多LLM 系统配置类
    """

    # LLM 提供商 API 密钥
    OPENAI_API_KEY: str = Field(
        description="OpenAI API 密钥，用于访问 GPT 系列模型",
        default="",
    )

    ANTHROPIC_API_KEY: str = Field(
        description="Anthropic API 密钥，用于访问 Claude 系列模型",
        default="",
    )

    GOOGLE_API_KEY: str = Field(
        description="Google API 密钥，用于访问 Gemini 系列模型",
        default="",
    )

    DEEPSEEK_API_KEY: str = Field(
        description="DeepSeek API 密钥，用于访问 DeepSeek 系列模型",
        default="",
    )

    OPENROUTER_API_KEY: str = Field(
        description="OpenRouter API 密钥，用于通过 OpenRouter 访问多个 LLM 供应商",
        default="",
    )

    # 多LLM 系统配置
    DEFAULT_LLM_PROVIDER: str = Field(
        description="默认 LLM 提供商（openai, anthropic, google, deepseek）",
        default="openrouter",
    )

    FALLBACK_LLM_PROVIDER: str = Field(
        description="备用 LLM 提供商，当主提供商不可用时使用",
        default="openai",
    )

    ENABLE_COST_TRACKING: bool = Field(
        description="启用成本追踪，监控 API 调用费用",
        default=True,
    )

    ENABLE_INTELLIGENT_ROUTING: bool = Field(
        description="启用智能路由，根据任务类型自动选择最适合的模型",
        default=True,
    )