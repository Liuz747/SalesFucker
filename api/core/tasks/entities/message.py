from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MessageType(StrEnum):
    """消息类型枚举"""
    ICE_BREAKING = "ice_breaking"
    FOLLOW_UP = "follow_up"
    HOLIDAY = "holiday"
    MARKETING = "marketing"
    PROMOTIONAL = "promotional"
    NOTIFICATION = "notification"
    GREETING = "greeting"


@dataclass
class MessagingResult:
    """消息发送结果"""
    success: bool
    message_id: str | None = None
    sent_at: datetime | None = None
    error_message: str | None = None
    metadata: dict | None = None