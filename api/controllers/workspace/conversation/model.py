"""
对话模型模块
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, Self

from pydantic import BaseModel, Field

from utils import get_current_datetime
from models import ThreadStatus, ThreadOrm
from .schema import ThreadMetadata, WorkflowData


class Thread(BaseModel):
    """对话线程数据模型"""
    
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")
    status: ThreadStatus = Field(default=ThreadStatus.ACTIVE, description="线程状态")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")
    processing_time: Optional[float] = Field(None, description="处理时间（毫秒）")
    metadata: ThreadMetadata = Field(description="线程元数据")
    
    @classmethod
    def to_model(cls, thread_orm: ThreadOrm) -> Self:
        """从ThreadOrm对象创建Thread Pydantic模型"""
        return cls(
            thread_id=thread_orm.thread_id,
            assistant_id=thread_orm.assistant_id,
            status=thread_orm.status,
            created_at=thread_orm.created_at,
            updated_at=thread_orm.updated_at,
            processing_time=None,
            metadata=ThreadMetadata(
                tenant_id=thread_orm.tenant_id,
                assistant_id=thread_orm.assistant_id
            )
        )
    
    def to_orm(self) -> ThreadOrm:
        """转换为ThreadOrm数据库模型对象"""
        return ThreadOrm(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            tenant_id=self.metadata.tenant_id,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class Workflow(BaseModel):
    """工作流模型"""
    
    id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    data: list[WorkflowData] = Field(description="工作流数据")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")