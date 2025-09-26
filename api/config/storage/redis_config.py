from typing import Optional

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    """
    Redis 配置
    """
    REDIS_HOST: str = Field(
        description="Redis 服务器主机地址",
        default="localhost",
    )

    REDIS_PORT: PositiveInt = Field(
        description="Redis 服务器端口号",
        default=6379,
    )

    REDIS_USERNAME: Optional[str] = Field(
        description="Redis 服务器用户名",
        default=None,
    )

    REDIS_PASSWORD: Optional[str] = Field(
        description="Redis 服务器密码",
        default="myredissecret",
    )

    REDIS_MAX_CONNECTIONS: PositiveInt = Field(
        description="Redis 最大连接数",
        default=10,
    )

    REDIS_SOCKET_TIMEOUT: float = Field(
        description="Redis 连接超时时间",
        default=5,
    )

    REDIS_CONNECT_TIMEOUT: float = Field(
        description="Redis 连接超时时间",
        default=5,
    )

    REDIS_TLS_ENABLED: bool = Field(
        description="是否启用 TLS",
        default=False,
    )

    REDIS_TLS_CA: Optional[str] = Field(
        description="Redis TLS CA",
        default=None,
    )

    REDIS_TLS_CERT: Optional[str] = Field(
        description="Redis TLS CERT",
        default=None,
    )

    REDIS_TTL: PositiveInt = Field(
        description="Redis 缓存时间 (秒)",
        default=7200,
    )

    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        return (
            f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}"
            f"@{self.REDIS_HOST}:{self.REDIS_PORT}"
        )