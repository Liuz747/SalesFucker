"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""
from datetime import datetime
from typing import Optional, Any, List, Self

from pydantic import BaseModel, Field, UUID4

# 从业务模型导入
from models import ConversationStatus, ThreadOrm
from utils import get_current_datetime


class InputContent(BaseModel):
    """消息内容模型"""
    
    role: str = Field(description="消息角色（user/assistant/system）")
    content: str = Field(description="消息内容", min_length=1)


class ThreadMetadata(BaseModel):
    """线程元数据模型"""
    
    tenant_id: Optional[UUID4] = Field(None, description="租户标识符")


class WorkflowData(BaseModel):
    """工作流数据模型"""
    
    type: str = Field(description="工作流数据类型")
    content: Any = Field(description="工作流数据内容")

class ThreadModel(BaseModel):
    """对话线程数据模型"""
    
    thread_id: UUID4 = Field(description="线程标识符")
    assistant_id: Optional[UUID4] = Field(None, description="助手标识符")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="线程状态")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")
    processing_time: Optional[float] = Field(None, description="处理时间（毫秒）")
    metadata: ThreadMetadata = Field(description="线程元数据")
    
    @classmethod
    def from_orm(cls, orm_obj: ThreadOrm) -> Self:
        """从ORM对象转换为业务模型"""
        return cls(
            thread_id=orm_obj.thread_id,
            assistant_id=orm_obj.assistant_id,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
            processing_time=orm_obj.processing_time,
            metadata=ThreadMetadata(tenant_id=orm_obj.tenant_id)
        )


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型"""
    
    thread_id: Optional[UUID4] = Field(None, description="线程标识符")
    metadata: Optional[ThreadMetadata] = Field(None, description="线程元数据")


class MessageCreateRequest(BaseModel):
    """消息创建请求模型"""
    
    assistant_id: UUID4 = Field(description="助手标识符")
    input: InputContent = Field(description="消息内容列表，包含role和content字段")
    callback_url: Optional[str] = Field(None, description="完成后回调的后端API地址")
    metadata: Optional[ThreadMetadata] = Field(None, description="线程元数据")


class CallbackPayload(BaseModel):
    """回调载荷模型"""
    
    run_id: UUID4 = Field(description="运行标识符")
    thread_id: UUID4 = Field(description="线程标识符")
    status: str = Field(description="运行状态 (completed/failed)")
    data: Optional[List[WorkflowData]] = Field(None, description="工作流处理结果")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    processing_time: float = Field(description="处理时间（毫秒）")
    completed_at: datetime = Field(description="完成时间")
    metadata: dict = Field(description="元数据信息")


class BackgroundRunStatus(BaseModel):
    """后台运行状态模型"""
    
    run_id: UUID4 = Field(description="运行标识符")
    thread_id: UUID4 = Field(description="线程标识符")
    status: str = Field(description="运行状态 (started/processing/completed/failed)")
    created_at: datetime = Field(description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始处理时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    processing_time: Optional[float] = Field(None, description="处理时间（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    callback_url: Optional[str] = Field(None, description="回调地址")
    callback_status: Optional[str] = Field(None, description="回调状态 (pending/success/failed)")
    retry_count: int = Field(default=0, description="重试次数")