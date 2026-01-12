from dataclasses import dataclass
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
class TriggerMessagingResult:
    """消息发送结果"""
    success: bool
    action: str | None = None
    detail: str | None = None
    metadata: dict | None = None
