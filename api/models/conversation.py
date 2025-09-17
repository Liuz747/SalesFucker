"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, Self

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum, String, Uuid, func

from schemas.conversation_schema import ThreadMetadata
from utils import get_current_datetime
from .base import Base
from .enums import ThreadStatus


class ThreadOrm(Base):
    """线程数据库ORM模型 - 优化云数据库性能"""
    
    __tablename__ = "threads"
    
    thread_id = Column(Uuid, primary_key=True)
    assistant_id = Column(Uuid, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    status = Column(Enum(ThreadStatus, name='thread_status'), default=ThreadStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
