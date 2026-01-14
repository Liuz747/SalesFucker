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

    TASK_QUEUE: str = Field(
        description="Temporal任务队列",
        default="mas-active-trigger",
    )

    MAX_CONCURRENT_ACTIVITIES: int = Field(
        description="最大并发活动数量",
        default=100,
    )

    WORKER_COUNT: int = Field(
        description="工作器数量",
        default=3,
    )

    @property
    def temporal_url(self) -> str:
        """获取Temporal服务器地址"""
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"