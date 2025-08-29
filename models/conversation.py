"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text
from sqlalchemy.sql import func

from utils import get_current_datetime
from models.base import Base


class ThreadMetadata(BaseModel):
    """线程元数据模型"""

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)


class ConversationStatus(StrEnum):
    """对话状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    PAUSED = "paused"


class InputType(StrEnum):
    """输入类型枚举"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class ThreadOrm(Base):
    """线程数据库ORM模型 - 优化云数据库性能"""
    
    __tablename__ = "threads"
    
    thread_id = Column(String(100), primary_key=True, index=True)
    assistant_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


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
