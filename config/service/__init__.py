"""
身份验证配置模块

包含所有身份验证相关配置，包括 JWT 和服务身份验证。
"""

from pydantic import Field
from pydantic_settings import BaseSettings

from .provider import LLMConfig

class AuthConfig(BaseSettings):
    """
    身份验证和 JWT 配置类
    """
    # 服务身份验证配置
    APP_KEY: str = Field(
        description="后端服务应用密钥，用于服务间身份验证",
        default="123",
    )

    APP_JWT_ISSUER: str = Field(
        description="JWT 令牌签发者标识",
        default="mas-ai-service",
    )

    APP_JWT_AUDIENCE: str = Field(
        description="JWT 令牌受众标识",
        default="ai-admin",
    )

    APP_TOKEN_TTL: int = Field(
        description="JWT 令牌过期时间（秒）",
        default=3600,
    )

class LogConfig(BaseSettings):
    """
    日志记录配置类
    """
    # 日志记录配置
    LOG_LEVEL: str = Field(
        description="日志记录级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）",
        default="INFO",
    )

    LOG_FILE: str = Field(
        description="日志文件存储路径",
        default="logs/mas.log",
    )

    ENABLE_REQUEST_LOGGING: bool = Field(
        description="启用请求和响应体日志记录",
        default=False,
    )

class ServiceConfig(AuthConfig, LLMConfig, LogConfig):
    """
    服务配置类
    """
    pass