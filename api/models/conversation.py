"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
"""

from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, BigInteger, String
from sqlalchemy.sql import func

from models.base import Base


class ThreadStatus(StrEnum):
    """对话状态枚举"""
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class InputType(StrEnum):
    """输入类型枚举"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class ThreadOrm(Base):
    """线程数据库ORM模型 - 优化云数据库性能"""
    
    __tablename__ = "threads"
    
    thread_id = Column(String, primary_key=True, index=True)
    assistant_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(ThreadStatus, name='thread_status'), default=ThreadStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkFlowOrm(Base):
    """工作流数据库ORM模型"""
    
    __tablename__ = "workflows"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    assistant_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)