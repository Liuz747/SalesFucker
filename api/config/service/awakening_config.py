"""
Thread Awakening Configuration

线程唤醒工作流配置模块
"""
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class AwakeningConfig(BaseSettings):
    """线程唤醒工作流配置"""

    AWAKENING_FIRST_ATTEMPT_DAYS: PositiveInt = Field(
        default=2,
        description="第一次唤醒的不活跃天数阈值"
    )

    AWAKENING_SECOND_ATTEMPT_DAYS: PositiveInt = Field(
        default=2,
        description="第二次唤醒的不活跃天数阈值"
    )

    MAX_AWAKENING_ATTEMPTS: PositiveInt = Field(
        default=2,
        description="最大唤醒消息发送次数"
    )

    AWAKENING_BATCH_SIZE: PositiveInt = Field(
        default=50,
        description="每批次处理的线程数量"
    )

    AWAKENING_SCAN_INTERVAL_HOURS: PositiveInt = Field(
        default=6,
        description="扫描间隔（小时）"
    )

    @property
    def first_attempt_seconds(self) -> int:
        """计算第一次唤醒的阈值（秒）"""
        return self.AWAKENING_FIRST_ATTEMPT_DAYS * 24 * 60 * 60

    @property
    def second_attempt_seconds(self) -> int:
        """计算第二次唤醒的阈值（秒）"""
        return self.AWAKENING_SECOND_ATTEMPT_DAYS * 24 * 60 * 60

    @property
    def scan_interval_seconds(self) -> int:
        """计算扫描间隔（秒）"""
        return self.AWAKENING_SCAN_INTERVAL_HOURS * 60 * 60
