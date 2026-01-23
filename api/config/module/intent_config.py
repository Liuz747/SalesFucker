"""
Intent Detection Configuration

配置意向检测的阈值参数，用于覆盖LLM返回的detected信号。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class IntentThresholdConfig(BaseSettings):
    """
    意向检测阈值配置

    用于基于confidence/strength分数自动覆盖LLM返回的detected信号。
    如果分数低于阈值，即使LLM返回detected=true，也会被覆盖为false。
    """

    # 素材发送意向阈值
    ASSETS_INTENT_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="素材发送意向的最低置信度阈值。低于此值时detected=false"
    )

    # 邀约到店意向阈值
    APPOINTMENT_INTENT_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="邀约到店意向的最低强度阈值。低于此值时detected=false"
    )

    # 音频输出意向阈值
    AUDIO_OUTPUT_INTENT_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="音频输出意向的最低置信度阈值。低于此值时detected=false"
    )

    # 是否启用阈值覆盖
    ENABLE_INTENT_THRESHOLD_OVERRIDE: bool = Field(
        default=True,
        description="是否启用基于阈值的意向检测覆盖。设为False则完全信任LLM返回的detected值"
    )