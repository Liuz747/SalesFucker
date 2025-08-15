"""
类型定义库

该模块定义系统中使用的类型别名和枚举类型。
提供类型安全的同时保持代码的可维护性。

核心功能:
- 消息类型定义
- 状态类型定义
- 策略类型定义
- 输入类型定义
"""

from .definitions import (
    MessageType,
    ComplianceStatus,
    MarketStrategy,
    PriorityLevel,
    InputType,
    ProcessingType,
    ProcessingStatus
)

__all__ = [
    "MessageType",
    "ComplianceStatus", 
    "MarketStrategy",
    "PriorityLevel",
    "InputType",
    "ProcessingType",
    "ProcessingStatus"
]