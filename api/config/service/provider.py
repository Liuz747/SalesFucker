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
        description="OpenRouter API 密钥，用于访问 OpenRouter 系列模型",
        default="",
    )

    DASHSCOPE_API_KEY: str = Field(
        description="阿里云通义千问 DashScope API 密钥，用于访问 Paraformer 语音转文字服务",
        default="",
    )

    MINIMAX_API_KEY: str = Field(
        description="MiniMax API 密钥，用于访问 TTS 语音合成服务",
        default="",
    )

    MINIMAX_VOICE_ID: str = Field(
        description="MiniMax 语音 ID，用于访问 TTS 语音合成服务",
        default="qianyu_test",
    )

    ZENMUX_API_KEY: str = Field(
        description="Zenmux API 密钥，用于访问 Zenmux 系列模型",
        default="",
    )
