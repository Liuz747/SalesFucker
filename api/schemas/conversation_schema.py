"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

from uuid import UUID
from typing import Optional, Any, Sequence

from pydantic import BaseModel, Field, field_validator

from models.enums import InputType


class InputContent(BaseModel):
    """通用输入内容模型（支持文本和多模态URL）"""

    type: InputType = Field(description="内容类型")
    content: str = Field(description="文本内容或URL（根据type字段）")

    @field_validator('content')
    @classmethod
    def validate_url_if_not_text(cls, v: str, info) -> str:
        """验证非文本类型必须是有效URL"""
        content_type = info.data.get('type')
        if content_type and content_type != InputType.TEXT:
            if not v.startswith(('http://', 'https://')):
                raise ValueError(f"无效的URL格式: {v}")
        return v


class ThreadMetadata(BaseModel):
    """线程元数据模型"""
    
    tenant_id: Optional[str] = Field(None, description="租户标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")


class WorkflowData(BaseModel):
    """工作流数据模型"""
    
    type: str = Field(description="工作流数据类型")
    content: Any = Field(description="工作流数据内容")


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型"""
    
    thread_id: Optional[UUID] = Field(None, description="线程标识符")


class MessageCreateRequest(BaseModel):
    """消息创建请求模型"""

    assistant_id: UUID = Field(description="助手标识符")
    input: str | Sequence[InputContent] = Field(description="纯文本输入或多模态内容列表")
    metadata: Optional[ThreadMetadata] = Field(None, description="线程元数据")


class CallbackPayload(BaseModel):
    """回调载荷模型"""
    
    run_id: UUID = Field(description="运行标识符")
    thread_id: UUID = Field(description="线程标识符")
    status: str = Field(description="运行状态 (completed/failed)")
    data: Optional[WorkflowData] = Field(None, description="工作流处理结果")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    processing_time: float = Field(description="处理时间（毫秒）")
    finished_at: str = Field(description="完成时间（ISO格式字符串）")
    metadata: dict = Field(description="元数据信息")
