"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
"""

from enum import StrEnum

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func

from models.base import Base


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
