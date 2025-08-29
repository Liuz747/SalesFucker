"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# 从业务模型导入
from models import ConversationStatus, ThreadOrm
from utils import get_current_datetime


class ThreadMetadata(BaseModel):
    """线程元数据模型"""

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)


class ThreadModel(BaseModel):
    """对话线程数据模型"""
    
    thread_id: str = Field(description="线程标识符")
    assistant_id: str = Field(description="助手标识符")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="线程状态")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")
    metadata: ThreadMetadata = Field(description="线程元数据")
    
    @classmethod
    def from_orm(cls, orm_obj: ThreadOrm) -> "ThreadModel":
        """从ORM对象转换为业务模型"""
        return cls(
            thread_id=orm_obj.thread_id,
            assistant_id=orm_obj.assistant_id,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
            metadata=ThreadMetadata(tenant_id=orm_obj.tenant_id)
        )


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型"""
    
    thread_id: Optional[str] = Field(None, description="线程标识符", min_length=1, max_length=100)
    assistant_id: str = Field(description="助手标识符", min_length=1, max_length=100)
    metadata: ThreadMetadata = Field(description="线程元数据，必须包含tenant_id")


class MessageCreateRequest(BaseModel):
    """消息创建请求模型"""
    
    assistant_id: str = Field(description="助手标识符", min_length=1, max_length=100)
    message: str = Field(description="用户消息内容", min_length=1)
    metadata: ThreadMetadata = Field(description="线程元数据，必须包含tenant_id")