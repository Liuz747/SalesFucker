"""
多模态附件系统

该模块定义了多模态消息中的附件类型和处理逻辑。
支持音频和图像文件的元数据管理、验证和处理状态跟踪。

核心功能:
- 附件基类和类型定义
- 文件格式验证和安全检查
- 处理状态跟踪和元数据管理
- 多租户数据隔离
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid
import mimetypes
from pathlib import Path

from utils import (
    get_current_datetime,
    ProcessingStatus,
    ProcessingType,
    MultiModalConstants,
    MessageConstants
)


class BaseAttachment(BaseModel):
    """
    多模态附件基类
    
    定义所有多模态附件的通用属性和验证逻辑。
    提供文件元数据管理、安全验证和处理状态跟踪。
    
    属性:
        attachment_id: 附件唯一标识符
        file_name: 原始文件名
        content_type: MIME内容类型
        file_size: 文件大小（字节）
        upload_path: 临时上传路径
        processing_status: 处理状态
        processing_type: 处理类型
        metadata: 附件元数据
        tenant_id: 租户标识符
        customer_id: 客户标识符
        created_at: 创建时间
        processed_at: 处理完成时间
    """
    
    # 基本信息
    attachment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="附件唯一标识符"
    )
    file_name: str = Field(description="原始文件名")
    content_type: str = Field(description="MIME内容类型")
    file_size: int = Field(description="文件大小（字节）")
    upload_path: Optional[str] = Field(None, description="临时上传路径")
    
    # 处理状态
    processing_status: ProcessingStatus = Field(
        ProcessingStatus.UPLOADING,
        description="当前处理状态"
    )
    processing_type: ProcessingType = Field(description="处理类型")
    
    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附件特定元数据"
    )
    
    # 租户信息
    tenant_id: str = Field(description="租户标识符")
    customer_id: Optional[str] = Field(None, description="客户标识符")
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=get_current_datetime,
        description="附件创建时间"
    )
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """验证文件大小"""
        if v <= 0:
            raise ValueError("文件大小必须大于0")
        return v
    
    def is_valid_format(self) -> bool:
        """检查文件格式是否有效"""
        raise NotImplementedError("子类必须实现格式验证")
    
    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return Path(self.file_name).suffix.lower().lstrip('.')
    
    def update_status(self, status: ProcessingStatus, metadata: Optional[Dict] = None):
        """更新处理状态"""
        self.processing_status = status
        if metadata:
            self.metadata.update(metadata)
        if status == ProcessingStatus.COMPLETED:
            self.processed_at = get_current_datetime()


class AudioAttachment(BaseAttachment):
    """
    音频附件类
    
    专用于处理音频文件的附件类型。
    支持多种音频格式的验证和音频特定元数据管理。
    
    属性:
        duration: 音频时长（秒）
        sample_rate: 采样率
        channels: 声道数
        language: 检测到的语言
        transcription: 转录文本
        confidence_score: 转录置信度
    """
    
    processing_type: ProcessingType = Field(
        default=ProcessingType.VOICE_TRANSCRIPTION,
        description="语音转录处理类型"
    )
    
    # 音频特定属性
    duration: Optional[float] = Field(None, description="音频时长（秒）")
    sample_rate: Optional[int] = Field(None, description="采样率")  
    channels: Optional[int] = Field(None, description="声道数")
    language: Optional[str] = Field(None, description="检测到的语言")
    
    # 处理结果
    transcription: Optional[str] = Field(None, description="转录文本")
    confidence_score: Optional[float] = Field(None, description="转录置信度")
    
    @validator('file_size')
    def validate_audio_size(cls, v):
        """验证音频文件大小"""
        if v > MultiModalConstants.MAX_AUDIO_SIZE:
            raise ValueError(f"音频文件大小超过限制 {MultiModalConstants.MAX_AUDIO_SIZE} bytes")
        return v
    
    @validator('duration')
    def validate_duration(cls, v):
        """验证音频时长"""
        if v is not None:
            if v < MultiModalConstants.MIN_AUDIO_DURATION:
                raise ValueError(f"音频时长不能少于 {MultiModalConstants.MIN_AUDIO_DURATION} 秒")
            if v > MultiModalConstants.MAX_AUDIO_DURATION:
                raise ValueError(f"音频时长不能超过 {MultiModalConstants.MAX_AUDIO_DURATION} 秒")
        return v
    
    def is_valid_format(self) -> bool:
        """检查音频格式是否有效"""
        extension = self.get_file_extension()
        return extension in MessageConstants.SUPPORTED_AUDIO_FORMATS
    
    def is_transcription_confident(self) -> bool:
        """检查转录结果是否可信"""
        return (
            self.confidence_score is not None and 
            self.confidence_score >= MultiModalConstants.MIN_VOICE_CONFIDENCE
        )


class ImageAttachment(BaseAttachment):
    """
    图像附件类
    
    专用于处理图像文件的附件类型。
    支持多种图像格式的验证和图像特定元数据管理。
    
    属性:
        width: 图像宽度
        height: 图像高度
        channels: 颜色通道数
        analysis_type: 分析类型（皮肤分析/产品识别）
        analysis_results: 分析结果
        confidence_scores: 置信度分数
        detected_objects: 检测到的对象
    """
    
    processing_type: ProcessingType = Field(
        default=ProcessingType.IMAGE_ANALYSIS,
        description="图像分析处理类型"
    )
    
    # 图像特定属性
    width: Optional[int] = Field(None, description="图像宽度")
    height: Optional[int] = Field(None, description="图像高度")
    channels: Optional[int] = Field(None, description="颜色通道数")
    
    # 分析配置
    analysis_type: Optional[str] = Field(None, description="分析类型")
    
    # 处理结果
    analysis_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="图像分析结果"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="各项分析的置信度分数"
    )
    detected_objects: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="检测到的对象列表"
    )
    
    @validator('file_size')
    def validate_image_size(cls, v):
        """验证图像文件大小"""
        if v > MultiModalConstants.MAX_IMAGE_SIZE:
            raise ValueError(f"图像文件大小超过限制 {MultiModalConstants.MAX_IMAGE_SIZE} bytes")
        return v
    
    @validator('width', 'height')
    def validate_dimensions(cls, v):
        """验证图像尺寸"""
        if v is not None:
            if v < MultiModalConstants.MIN_IMAGE_WIDTH:
                raise ValueError(f"图像尺寸不能小于 {MultiModalConstants.MIN_IMAGE_WIDTH}px")
        return v
    
    def is_valid_format(self) -> bool:
        """检查图像格式是否有效"""
        extension = self.get_file_extension()
        return extension in MessageConstants.SUPPORTED_IMAGE_FORMATS
    
    def is_analysis_confident(self, analysis_key: str = None) -> bool:
        """检查分析结果是否可信"""
        if analysis_key:
            score = self.confidence_scores.get(analysis_key, 0)
            return score >= MultiModalConstants.MIN_IMAGE_CONFIDENCE
        
        # 检查所有分析结果的平均置信度
        if not self.confidence_scores:
            return False
        
        avg_confidence = sum(self.confidence_scores.values()) / len(self.confidence_scores)
        return avg_confidence >= MultiModalConstants.MIN_IMAGE_CONFIDENCE
    
    def set_analysis_type(self, analysis_type: str):
        """设置分析类型"""
        valid_types = [
            ProcessingType.SKIN_ANALYSIS,
            ProcessingType.PRODUCT_RECOGNITION,
            ProcessingType.IMAGE_ANALYSIS
        ]
        if analysis_type not in valid_types:
            raise ValueError(f"无效的分析类型: {analysis_type}")
        
        self.analysis_type = analysis_type
        if analysis_type == ProcessingType.SKIN_ANALYSIS:
            self.processing_type = ProcessingType.SKIN_ANALYSIS
        elif analysis_type == ProcessingType.PRODUCT_RECOGNITION:
            self.processing_type = ProcessingType.PRODUCT_RECOGNITION