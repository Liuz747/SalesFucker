"""
Intent Analysis Models

该模块定义了意向分析的所有数据模型，使用Pydantic进行自动验证和类型安全。

核心功能:
- 自动验证字段类型和取值范围
- 提供默认值，简化降级处理
- 支持JSON序列化/反序列化
- 类型安全的数据访问
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from utils import to_isoformat


# ============================================================
# 实体相关模型
# ============================================================

class ExtractedEntities(BaseModel):
    """提取的实体信息模型"""
    service: Optional[str] = Field(default=None, description="服务项目名称")
    name: Optional[str] = Field(default=None, description="客户姓名")
    phone: Optional[str] = Field(default=None, description="联系电话")
    time_expression: Optional[str] = Field(default=None, description="时间表达式")


class AssetType(BaseModel):
    """素材类型详细信息"""
    type: str = Field(..., description="素材类型标识")
    category: Literal["visual", "information", "proof", "service"] = Field(..., description="素材分类")
    description: str = Field(default="", description="素材描述")
    priority: float = Field(default=0.5, ge=0.0, le=1.0, description="优先级")
    specifics: list[str] = Field(default_factory=list, description="具体需求列表")


# ============================================================
# 意向分析模型
# ============================================================

class AssetsIntent(BaseModel):
    """素材发送意向模型"""
    detected: bool = Field(default=False, description="是否检测到素材意向")
    urgency_level: Literal["high", "medium", "low"] = Field(default="medium", description="紧急程度")
    asset_types: list[AssetType] = Field(default_factory=list, description="需要的素材类型列表")
    keywords: list[str] = Field(default_factory=list, description="用于搜索素材的关键词列表")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="分析置信度"
    )
    summary: str = Field(default="", description="意向摘要")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_score_range(cls, v: float) -> float:
        """确保分数在0-1范围内"""
        if v is None:
            return 0.5
        return max(0.0, min(1.0, float(v)))


class AppointmentIntent(BaseModel):
    """邀约到店意向模型"""
    detected: bool = Field(default=False, description="是否检测到邀约意向")
    intent_strength: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="意向强度"
    )
    time_window: str = Field(default="unknown", description="时间窗口")
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities, description="提取的实体信息")
    summary: str = Field(default="", description="意向摘要")

    @field_validator("intent_strength", mode="before")
    @classmethod
    def clamp_score_range(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class AudioOutputIntent(BaseModel):
    """音频输出意向模型"""
    detected: bool = Field(default=False, description="是否检测到音频输出意向")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="分析置信度"
    )
    trigger_reason: str = Field(default="none", description="触发原因")
    summary: str = Field(default="", description="意向摘要")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence_range(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


# ============================================================
# 业务输出模型
# ============================================================

class IntentAnalysisResult(BaseModel):
    """意向分析完整结果模型"""
    assets_intent: AssetsIntent = Field(default_factory=AssetsIntent, description="素材发送意向")
    appointment_intent: AppointmentIntent = Field(default_factory=AppointmentIntent, description="邀约到店意向")
    audio_output_intent: AudioOutputIntent = Field(default_factory=AudioOutputIntent, description="音频输出意向")
    timestamp: Optional[str] = Field(default_factory=to_isoformat, description="分析时间戳")
    input_tokens: int = Field(default=0, description="输入token数")
    output_tokens: int = Field(default=0, description="输出token数")
    error: Optional[str] = Field(default=None, description="错误信息")
