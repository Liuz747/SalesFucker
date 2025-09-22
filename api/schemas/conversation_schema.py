"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

from uuid import UUID
from typing import Optional, Any, List

from pydantic import BaseModel, Field


class InputContent(BaseModel):
    """消息内容模型"""
    
    role: str = Field(description="消息角色（user/assistant/system）")
    content: str = Field(description="消息内容", min_length=1)


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
    input: InputContent = Field(description="消息内容列表，包含role和content字段")
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
