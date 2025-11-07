"""
简化的Temporal工作流数据模型

仅包含工作流安全的模型定义，避免Temporal沙盒限制。
"""

from datetime import datetime
from enum import StrEnum
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    """消息类型枚举"""
    ICE_BREAKING = "ice_breaking"
    FOLLOW_UP = "follow_up"
    HOLIDAY = "holiday"
    MARKETING = "marketing"
    PROMOTIONAL = "promotional"
    NOTIFICATION = "notification"
    GREETING = "greeting"


class MessagePriority(StrEnum):
    """消息优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessagingResult(BaseModel):
    """消息发送结果 - 工作流安全版本"""
    success: bool = Field(description="是否成功")
    message_id: Optional[str] = Field(default=None, description="消息ID")
    sent_at: Optional[datetime] = Field(default=None, description="发送时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")