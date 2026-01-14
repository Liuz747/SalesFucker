"""
Thread Awakening Configuration

线程唤醒工作流配置模块
"""

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class AwakeningConfig(BaseSettings):
    """线程唤醒工作流配置"""

    INACTIVE_INTERVAL_DAYS: PositiveInt = Field(
        default=2,
        description="唤醒重试间隔天数（线程不活跃多少天后触发唤醒）"
    )

    MAX_AWAKENING_ATTEMPTS: PositiveInt = Field(
        default=2,
        description="最大唤醒消息发送次数"
    )

    AWAKENING_BATCH_SIZE: PositiveInt = Field(
        default=300,
        description="每批次处理的线程数量"
    )

    AWAKENING_SCAN_INTERVAL_HOURS: PositiveInt = Field(
        default=6,
        description="扫描间隔（小时）"
    )

    # DND (Do Not Disturb) 配置
    DND_ENABLED: bool = Field(
        default=True,
        description="是否启用免打扰功能"
    )

    DND_START_HOUR: int = Field(
        default=0,
        ge=0,
        le=23,
        description="免打扰开始时间（小时，24小时制，默认0点）"
    )

    DND_END_HOUR: int = Field(
        default=8,
        ge=0,
        le=23,
        description="免打扰结束时间（小时，24小时制，默认8点）"
    )
