"""
部署配置模块

应用程序部署相关的配置设置，包括基本应用信息、API服务、日志和性能配置。
"""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class DeploymentConfig(BaseSettings):
    """
    应用程序部署配置类
    """

    # 应用程序基本信息
    APP_NAME: str = Field(
        description="应用程序名称，用于标识和日志记录",
        default="MAS Marketing Agent System",
    )

    DEBUG: bool = Field(
        description="启用调试模式，提供额外的日志记录和开发功能",
        default=False,
    )

    APP_HOST: str = Field(
        description="API 服务监听主机地址",
        default="0.0.0.0",
    )

    APP_PORT: int = Field(
        description="API 服务监听端口号",
        default=8000,
    )

    APP_ENV: str = Field(
        description="部署环境标识（如 'PRODUCTION', 'DEVELOPMENT'），默认为生产环境",
        default="PRODUCTION",
    )

    # 回调配置
    CALLBACK_URL: HttpUrl = Field(
        description="后台工作流完成后的回调URL地址",
        default=None,
    )
