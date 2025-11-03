"""
Temporal工作流引擎配置
"""
from pydantic import Field
from pydantic_settings import BaseSettings


class TemporalConfig(BaseSettings):
    """
    Temporal配置

    用于事件调度和工作流编排的配置参数。
    """
    TEMPORAL_HOST: str = Field(
        description="Temporal服务器主机地址",
        default="localhost",
    )

    TEMPORAL_PORT: int = Field(
        description="Temporal服务器端口号",
        default=7233,
    )

    TEMPORAL_NAMESPACE: str = Field(
        description="Temporal命名空间",
        default="default",
    )

    TEMPORAL_RPC_TIMEOUT: int = Field(
        description="Temporal RPC调用超时时间（秒）",
        default=30,
    )

    @property
    def temporal_url(self) -> str:
        """获取Temporal服务器地址"""
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"