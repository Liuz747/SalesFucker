"""
Langfuse追踪配置模块

提供Langfuse集成所需的配置管理和客户端初始化。
用于多智能体工作流的可视化追踪和监控。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class TracerConfig(BaseSettings):
    
    LANGFUSE_PUBLIC_KEY: str = Field(
        description="Langfuse公钥",
        default="",
    )

    LANGFUSE_SECRET_KEY: str = Field(
        description="Langfuse私钥",
        default="",
    )

    LANGFUSE_HOST: str = Field(
        description="Langfuse主机",
        default="http://localhost:3000",
    )