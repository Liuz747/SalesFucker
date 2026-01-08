from enum import StrEnum


class EventType(StrEnum):
    """事件类型"""
    INVITATION = "invitation"
    FOLLOWUP = "follow_up"
    INACTIVE = "inactive"