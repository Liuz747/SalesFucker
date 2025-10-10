"""
类型定义模块

该模块定义系统中使用的类型别名和枚举类型。
提供类型安全的同时保持代码的可维护性。

核心功能:
- 消息类型定义
- 状态类型定义
- 策略类型定义
- 输入类型定义
"""

from enum import Enum

from libs.constants import MessageConstants


class MessageType(str, Enum):
    """消息类型枚举"""
    QUERY = MessageConstants.QUERY
    RESPONSE = MessageConstants.RESPONSE
    NOTIFICATION = MessageConstants.NOTIFICATION
    TRIGGER = MessageConstants.TRIGGER
    SUGGESTION = MessageConstants.SUGGESTION
