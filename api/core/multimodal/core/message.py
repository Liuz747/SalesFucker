"""
多模态消息系统

该模块扩展了基础消息系统以支持多模态内容处理。
与现有AgentMessage和ConversationState无缝集成，保持向后兼容性。

核心功能:
- 多模态消息封装和处理
- 附件管理和验证
- 处理结果聚合
- 异步处理状态跟踪
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

from core.agents.base import AgentMessage, ConversationState
from utils import (
    get_current_datetime,
    InputType,
    ProcessingStatus,
    ProcessingType,
    MultiModalConstants
)
from .attachment import BaseAttachment, AudioAttachment, ImageAttachment


class ProcessingResult(BaseModel):
    """
    多模态处理结果类
    
    封装单个附件的处理结果，包含状态、结果数据和元数据。
    
    属性:
        attachment_id: 关联的附件ID
        processing_type: 处理类型
        status: 处理状态
        result_data: 处理结果数据
        confidence_score: 置信度分数
        processing_time_ms: 处理时间（毫秒）
        error_message: 错误信息
        metadata: 结果元数据
    """
    
    attachment_id: str = Field(description="关联的附件ID")
    processing_type: ProcessingType = Field(description="处理类型")
    status: ProcessingStatus = Field(description="处理状态")
    
    # 结果数据
    result_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="处理结果数据"
    )
    confidence_score: Optional[float] = Field(None, description="整体置信度分数")
    
    # 性能指标
    processing_time_ms: Optional[int] = Field(None, description="处理时间（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="处理结果元数据"
    )
    
    created_at: datetime = Field(
        default_factory=get_current_datetime,
        description="结果创建时间"
    )
    
    def is_successful(self) -> bool:
        """检查处理是否成功"""
        return self.status == ProcessingStatus.COMPLETED and self.error_message is None
    
    def is_confident(self) -> bool:
        """检查结果是否可信"""
        if self.confidence_score is None:
            return False
        
        # 根据处理类型使用不同的置信度阈值
        if self.processing_type == ProcessingType.VOICE_TRANSCRIPTION:
            return self.confidence_score >= MultiModalConstants.MIN_VOICE_CONFIDENCE
        elif self.processing_type in [ProcessingType.IMAGE_ANALYSIS, ProcessingType.PRODUCT_RECOGNITION]:
            return self.confidence_score >= MultiModalConstants.MIN_IMAGE_CONFIDENCE
        elif self.processing_type == ProcessingType.SKIN_ANALYSIS:
            return self.confidence_score >= MultiModalConstants.MIN_SKIN_ANALYSIS_CONFIDENCE
        
        return self.confidence_score >= 0.5


class MultiModalMessage(AgentMessage):
    """
    多模态消息类
    
    扩展AgentMessage以支持多模态内容，包括音频和图像附件。
    完全向后兼容，保持现有消息系统的所有功能。
    
    属性:
        attachments: 附件列表
        processing_results: 处理结果列表
        multimodal_context: 多模态上下文信息
        combined_content: 整合后的内容（文本+转录+分析结果）
    """
    
    # 多模态特定属性
    attachments: List[BaseAttachment] = Field(
        default_factory=list,
        description="多模态附件列表"
    )
    processing_results: List[ProcessingResult] = Field(
        default_factory=list,
        description="处理结果列表"
    )
    multimodal_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="多模态处理上下文"
    )
    combined_content: Optional[str] = Field(None, description="整合后的文本内容")
    
    @validator('attachments')
    def validate_attachments(cls, v):
        """验证附件列表"""
        if len(v) > MultiModalConstants.MAX_BATCH_IMAGES:
            raise ValueError(f"附件数量不能超过 {MultiModalConstants.MAX_BATCH_IMAGES}")
        return v
    
    def add_attachment(self, attachment: BaseAttachment) -> str:
        """添加附件"""
        if len(self.attachments) >= MultiModalConstants.MAX_BATCH_IMAGES:
            raise ValueError(f"附件数量已达上限 {MultiModalConstants.MAX_BATCH_IMAGES}")
        
        attachment.tenant_id = self.tenant_id
        attachment.customer_id = self.customer_id
        self.attachments.append(attachment)
        
        # 更新输入类型
        if isinstance(attachment, AudioAttachment):
            if self.context.get('input_type') == InputType.TEXT:
                self.context['input_type'] = InputType.VOICE
            elif self.context.get('input_type') in [InputType.IMAGE, InputType.VOICE]:
                self.context['input_type'] = InputType.MULTIMODAL
        elif isinstance(attachment, ImageAttachment):
            if self.context.get('input_type') == InputType.TEXT:
                self.context['input_type'] = InputType.IMAGE
            elif self.context.get('input_type') in [InputType.VOICE, InputType.IMAGE]:
                self.context['input_type'] = InputType.MULTIMODAL
        
        return attachment.attachment_id
    
    def add_processing_result(self, result: ProcessingResult):
        """添加处理结果"""
        self.processing_results.append(result)
        
        # 更新附件状态
        for attachment in self.attachments:
            if attachment.attachment_id == result.attachment_id:
                attachment.update_status(result.status, result.metadata)
                break
    
    def get_audio_attachments(self) -> List[AudioAttachment]:
        """获取音频附件"""
        return [att for att in self.attachments if isinstance(att, AudioAttachment)]
    
    def get_image_attachments(self) -> List[ImageAttachment]:
        """获取图像附件"""
        return [att for att in self.attachments if isinstance(att, ImageAttachment)]
    
    def get_transcriptions(self) -> List[str]:
        """获取所有转录文本"""
        transcriptions = []
        for attachment in self.get_audio_attachments():
            if attachment.transcription and attachment.is_transcription_confident():
                transcriptions.append(attachment.transcription)
        return transcriptions
    
    def get_analysis_results(self) -> Dict[str, Any]:
        """获取所有图像分析结果"""
        results = {}
        for attachment in self.get_image_attachments():
            if attachment.analysis_results and attachment.is_analysis_confident():
                results[attachment.attachment_id] = attachment.analysis_results
        return results
    
    def update_combined_content(self):
        """更新整合后的内容"""
        content_parts = []
        
        # 添加原始文本内容
        if hasattr(self, 'payload') and self.payload.get('message'):
            content_parts.append(self.payload['message'])
        
        # 添加转录文本
        transcriptions = self.get_transcriptions()
        if transcriptions:
            content_parts.extend(transcriptions)
        
        # 添加图像分析摘要
        analysis_results = self.get_analysis_results()
        for attachment_id, results in analysis_results.items():
            if results.get('summary'):
                content_parts.append(f"图像分析: {results['summary']}")
        
        self.combined_content = " ".join(content_parts) if content_parts else None
    
    def is_processing_complete(self) -> bool:
        """检查所有附件是否处理完成"""
        if not self.attachments:
            return True
        
        return all(
            att.processing_status in [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR]
            for att in self.attachments
        )
    
    def has_processing_errors(self) -> bool:
        """检查是否有处理错误"""
        return any(
            att.processing_status == ProcessingStatus.ERROR
            for att in self.attachments
        )
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """获取处理摘要"""
        return {
            'total_attachments': len(self.attachments),
            'audio_count': len(self.get_audio_attachments()),
            'image_count': len(self.get_image_attachments()),
            'completed_count': len([
                att for att in self.attachments 
                if att.processing_status == ProcessingStatus.COMPLETED
            ]),
            'error_count': len([
                att for att in self.attachments 
                if att.processing_status == ProcessingStatus.ERROR
            ]),
            'is_complete': self.is_processing_complete(),
            'has_errors': self.has_processing_errors()
        }


class MultiModalConversationState(ConversationState):
    """
    多模态对话状态类
    
    扩展ConversationState以支持多模态处理状态跟踪。
    完全向后兼容现有的对话状态管理。
    
    属性:
        multimodal_processing: 多模态处理状态
        attachment_queue: 待处理附件队列
        processing_timeline: 处理时间线
        multimodal_results: 多模态处理结果汇总
    """
    
    # 多模态处理状态
    multimodal_processing: Dict[str, Any] = Field(
        default_factory=dict,
        description="多模态处理状态跟踪"
    )
    attachment_queue: List[str] = Field(
        default_factory=list,
        description="待处理附件ID队列"
    )
    processing_timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="处理事件时间线"
    )
    multimodal_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="多模态处理结果汇总"
    )
    
    def add_processing_event(self, event_type: str, attachment_id: str = None, **kwargs):
        """添加处理事件到时间线"""
        event = {
            'timestamp': get_current_datetime(),
            'event_type': event_type,
            'attachment_id': attachment_id,
            **kwargs
        }
        self.processing_timeline.append(event)
    
    def update_multimodal_status(self, status: str, details: Dict[str, Any] = None):
        """更新多模态处理状态"""
        self.multimodal_processing.update({
            'status': status,
            'updated_at': get_current_datetime(),
            'details': details or {}
        })
    
    def is_multimodal_complete(self) -> bool:
        """检查多模态处理是否完成"""
        return (
            not self.attachment_queue and
            self.multimodal_processing.get('status') == 'completed'
        )