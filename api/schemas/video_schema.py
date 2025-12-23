"""
视频生成请求响应模式

该模块定义视频生成API的请求和响应数据结构。
支持文本生成视频(T2V)和图像生成视频(I2V)。
"""

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from .responses import BaseResponse


class VideoModel(StrEnum):
    """支持的视频生成模型"""
    WAN_2_6_T2V = "wan2.6-t2v"          # 文本生成视频
    WAN_2_6_I2V = "wan2.6-i2v"          # 图像生成视频


class VideoSize(StrEnum):
    """视频分辨率选项"""
    LANDSCAPE_720P = "1280*720"   # 横屏720P
    PORTRAIT_720P = "720*1280"    # 竖屏720P
    SQUARE_960 = "960*960"        # 正方形960


class InputReferenceType(StrEnum):
    """输入参考类型"""
    IMAGE = "image"
    VIDEO = "video"


class VideoTaskStatus(StrEnum):
    """视频任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class InputReference(BaseModel):
    """输入参考内容模型"""

    type: InputReferenceType = Field(description="参考类型：image或video")
    url: str = Field(description="参考内容的URL地址")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError(f"无效的URL格式: {v}")
        return v


class VideoGenerationRequest(BaseModel):
    """视频生成请求模型"""

    session_id: str = Field(
        description="会话ID，作为任务唯一标识",
        min_length=1,
        max_length=128
    )
    prompt: str = Field(
        description="视频内容的文本描述，最多1500字符",
        max_length=1500
    )
    model: VideoModel = Field(
        default=VideoModel.WAN_2_6_T2V,
        description="视频生成模型"
    )
    size: VideoSize = Field(
        default=VideoSize.LANDSCAPE_720P,
        description="视频分辨率"
    )
    length: int = Field(
        default=5,
        ge=5,
        le=15,
        description="视频时长（秒），支持5/10/15秒"
    )
    input_reference: Optional[InputReference] = Field(
        default=None,
        description="输入参考（图片或视频URL），用于图生视频或视频续写"
    )
    negative_prompt: Optional[str] = Field(
        default=None,
        max_length=500,
        description="负面提示词，描述不希望出现的内容"
    )
    prompt_extend: bool = Field(
        default=True,
        description="是否启用LLM提示词优化"
    )

    @field_validator('length')
    @classmethod
    def validate_length(cls, v: int) -> int:
        """验证视频时长在允许范围内"""
        if v not in [5, 10, 15]:
            raise ValueError("视频时长必须是5、10或15秒")
        return v


class VideoGenerationResponse(BaseResponse):
    """视频生成提交响应"""

    session_id: str = Field(description="会话ID")
    status: VideoTaskStatus = Field(description="任务状态")


class VideoStatusResponse(BaseModel):
    """视频任务状态响应"""

    session_id: str = Field(description="会话ID")
    status: VideoTaskStatus = Field(description="任务状态")
    video_url: Optional[str] = Field(default=None, description="生成的视频URL")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: int = Field(description="创建时间（毫秒时间戳）")
    finished_at: Optional[int] = Field(default=None, description="完成时间（毫秒时间戳）")


class VideoCallbackPayload(BaseModel):
    """视频生成完成回调载荷"""

    session_id: str = Field(description="会话ID")
    tenant_id: str = Field(description="租户标识符")
    status: str = Field(description="任务状态 (succeeded/failed)")
    video_url: Optional[str] = Field(default=None, description="生成的视频URL")
    error: Optional[str] = Field(default=None, description="错误信息")
    processing_time: float = Field(description="处理时间（毫秒）")
