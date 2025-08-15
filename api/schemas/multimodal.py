"""
多模态处理相关数据模型

该模块定义了多模态处理（语音、图像）相关的请求和响应数据模型。

核心模型:
- MultimodalRequest: 多模态处理请求
- VoiceProcessingRequest: 语音处理请求
- ImageAnalysisRequest: 图像分析请求
- MultimodalResponse: 多模态处理响应
- ProcessingStatusResponse: 处理状态响应
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .requests import BaseRequest
from .responses import AsyncTaskResponse, SuccessResponse


class ProcessingType(str, Enum):
    """处理类型枚举"""

    VOICE_TO_TEXT = "voice_to_text"
    IMAGE_ANALYSIS = "image_analysis"
    COMBINED_ANALYSIS = "combined_analysis"


class VoiceFormat(str, Enum):
    """语音格式枚举"""

    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    OGG = "ogg"


class ImageFormat(str, Enum):
    """图像格式枚举"""

    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"


class AnalysisType(str, Enum):
    """分析类型枚举"""

    SKIN_ANALYSIS = "skin_analysis"
    PRODUCT_RECOGNITION = "product_recognition"
    GENERAL_ANALYSIS = "general_analysis"


class MultimodalRequest(BaseRequest):
    """
    多模态处理请求模型
    """

    tenant_id: str = Field(description="租户ID", min_length=3, max_length=50)

    customer_id: Optional[str] = Field(None, description="客户ID")

    processing_type: ProcessingType = Field(description="处理类型")

    language: str = Field("zh-CN", description="语言代码（用于语音识别）")

    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="处理上下文"
    )

    async_processing: bool = Field(False, description="是否使用异步处理")

    callback_url: Optional[str] = Field(None, description="异步处理完成后的回调URL")


class VoiceProcessingRequest(MultimodalRequest):
    """
    语音处理请求模型
    """

    processing_type: ProcessingType = Field(
        default=ProcessingType.VOICE_TO_TEXT, description="固定为语音处理类型"
    )

    audio_format: VoiceFormat = Field(description="音频格式")

    duration_seconds: Optional[float] = Field(
        None, ge=0.1, le=300, description="音频时长（秒），最长5分钟"
    )

    enable_emotion_detection: bool = Field(False, description="是否启用情感检测")

    enable_sentiment_analysis: bool = Field(True, description="是否启用情感分析")

    noise_reduction: bool = Field(True, description="是否启用降噪")


class ImageAnalysisRequest(MultimodalRequest):
    """
    图像分析请求模型
    """

    processing_type: ProcessingType = Field(
        default=ProcessingType.IMAGE_ANALYSIS, description="固定为图像分析类型"
    )

    image_format: ImageFormat = Field(description="图像格式")

    analysis_types: List[AnalysisType] = Field(
        description="要执行的分析类型列表", min_items=1
    )

    image_quality: Optional[str] = Field(
        None, pattern="^(low|medium|high)$", description="图像质量要求"
    )

    max_image_size_mb: float = Field(
        10.0, ge=0.1, le=50.0, description="最大图像大小（MB）"
    )

    detect_products: bool = Field(True, description="是否检测化妆品产品")

    analyze_skin_condition: bool = Field(False, description="是否分析肌肤状况")


class BatchMultimodalRequest(BaseRequest):
    """
    批量多模态处理请求模型
    """

    tenant_id: str = Field(description="租户ID", min_length=3)

    requests: List[Union[VoiceProcessingRequest, ImageAnalysisRequest]] = Field(
        description="批量处理请求列表", min_items=1, max_items=20
    )

    parallel_processing: bool = Field(True, description="是否并行处理")

    @field_validator("requests")
    def validate_batch_size(cls, v):
        """验证批量大小"""
        if len(v) > 20:
            raise ValueError("批量处理请求数不能超过20")
        return v


# 响应模型


class VoiceProcessingResult(BaseModel):
    """语音处理结果模型"""

    transcript: str = Field(description="转录文本")
    confidence: float = Field(description="识别置信度", ge=0, le=1)
    language_detected: str = Field(description="检测到的语言")

    # 时间戳信息
    segments: Optional[List[Dict[str, Any]]] = Field(None, description="分段时间戳信息")

    # 情感分析
    sentiment: Optional[Dict[str, Any]] = Field(None, description="情感分析结果")

    emotion: Optional[Dict[str, Any]] = Field(None, description="情绪检测结果")

    # 技术指标
    audio_quality: Optional[str] = Field(None, description="音频质量评估")
    noise_level: Optional[float] = Field(None, description="噪音水平")


class ImageAnalysisResult(BaseModel):
    """图像分析结果模型"""

    analysis_types: List[AnalysisType] = Field(description="执行的分析类型")

    # 基础信息
    image_properties: Dict[str, Any] = Field(description="图像属性")
    quality_assessment: Dict[str, Any] = Field(description="质量评估")

    # 分析结果
    detected_objects: Optional[List[Dict[str, Any]]] = Field(
        None, description="检测到的对象"
    )

    skin_analysis: Optional[Dict[str, Any]] = Field(None, description="肌肤分析结果")

    product_recognition: Optional[List[Dict[str, Any]]] = Field(
        None, description="产品识别结果"
    )

    color_analysis: Optional[Dict[str, Any]] = Field(None, description="色彩分析")

    # 建议
    recommendations: Optional[List[str]] = Field(None, description="基于分析的建议")


class ProcessingMetadata(BaseModel):
    """处理元数据模型"""

    processing_id: str = Field(description="处理ID")
    processing_type: ProcessingType = Field(description="处理类型")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_ms: Optional[float] = Field(None, description="处理时长（毫秒）")

    # 资源使用
    resources_used: Optional[Dict[str, Any]] = Field(None, description="资源使用情况")

    # 模型信息
    models_used: List[str] = Field(description="使用的模型列表")
    provider_info: Optional[Dict[str, Any]] = Field(None, description="提供商信息")


class MultimodalResponse(SuccessResponse[Dict[str, Any]]):
    """
    多模态处理响应模型
    """

    processing_id: str = Field(description="处理ID")
    processing_type: ProcessingType = Field(description="处理类型")

    # 处理结果
    voice_result: Optional[VoiceProcessingResult] = Field(
        None, description="语音处理结果"
    )

    image_result: Optional[ImageAnalysisResult] = Field(
        None, description="图像分析结果"
    )

    # 元数据
    metadata: ProcessingMetadata = Field(description="处理元数据")

    # 后续建议
    next_steps: Optional[List[str]] = Field(None, description="后续处理建议")


class ProcessingStatusResponse(SuccessResponse[Dict[str, Any]]):
    """
    处理状态响应模型
    """

    processing_id: str = Field(description="处理ID")
    status: str = Field(
        description="处理状态",
        pattern="^(pending|processing|completed|failed|cancelled)$",
    )

    progress: float = Field(description="处理进度", ge=0, le=100)

    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")

    current_stage: Optional[str] = Field(None, description="当前处理阶段")

    error_message: Optional[str] = Field(None, description="错误消息（如果失败）")

    result_url: Optional[str] = Field(None, description="结果获取URL（如果完成）")


class BatchProcessingResponse(SuccessResponse[List[Dict[str, Any]]]):
    """
    批量处理响应模型
    """

    batch_id: str = Field(description="批次ID")
    total_items: int = Field(description="总项目数")
    completed_items: int = Field(description="已完成项目数")
    failed_items: int = Field(description="失败项目数")

    # 详细结果
    results: List[Union[MultimodalResponse, Dict[str, Any]]] = Field(
        description="处理结果列表"
    )

    # 批次统计
    processing_stats: Dict[str, Any] = Field(description="处理统计")

    # 错误汇总
    error_summary: Optional[Dict[str, Any]] = Field(None, description="错误汇总")


class MultimodalCapabilitiesResponse(SuccessResponse[Dict[str, Any]]):
    """
    多模态能力响应模型
    """

    supported_formats: Dict[str, List[str]] = Field(description="支持的格式")

    processing_limits: Dict[str, Any] = Field(description="处理限制")

    available_models: Dict[str, List[str]] = Field(description="可用模型")

    features: List[str] = Field(description="支持的功能列表")

    performance_benchmarks: Optional[Dict[str, float]] = Field(
        None, description="性能基准"
    )
