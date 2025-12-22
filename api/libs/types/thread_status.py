from enum import StrEnum


class ThreadStatus(StrEnum):
    """对话状态枚举"""
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    BUSY = "BUSY"
    FAILED = "FAILED"