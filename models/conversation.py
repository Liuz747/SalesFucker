"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型。
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from utils import get_current_datetime


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


class ThreadModel(BaseModel):
    """对话线程数据模型"""
    
    thread_id: str = Field(description="线程标识符")
    assistant_id: str = Field(description="助手标识符")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="线程状态")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")
    metadata: ThreadMetadata = Field(default_factory=ThreadMetadata, description="线程元数据")
