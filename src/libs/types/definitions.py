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

from src.libs.constants import MessageConstants, StatusConstants, WorkflowConstants


class MessageType(str, Enum):
    """消息类型枚举"""
    QUERY = MessageConstants.QUERY
    RESPONSE = MessageConstants.RESPONSE
    NOTIFICATION = MessageConstants.NOTIFICATION
    TRIGGER = MessageConstants.TRIGGER
    SUGGESTION = MessageConstants.SUGGESTION


class ComplianceStatus(str, Enum):
    """合规状态枚举"""
    APPROVED = StatusConstants.APPROVED
    FLAGGED = StatusConstants.FLAGGED
    BLOCKED = StatusConstants.BLOCKED


class MarketStrategy(str, Enum):
    """市场策略枚举"""
    PREMIUM = WorkflowConstants.PREMIUM_STRATEGY
    BUDGET = WorkflowConstants.BUDGET_STRATEGY
    YOUTH = WorkflowConstants.YOUTH_STRATEGY
    MATURE = WorkflowConstants.MATURE_STRATEGY


class PriorityLevel(str, Enum):
    """优先级枚举"""
    LOW = MessageConstants.LOW_PRIORITY
    MEDIUM = MessageConstants.MEDIUM_PRIORITY
    HIGH = MessageConstants.HIGH_PRIORITY
    URGENT = MessageConstants.URGENT_PRIORITY


class InputType(str, Enum):
    """输入类型枚举"""
    TEXT = MessageConstants.TEXT_INPUT
    VOICE = MessageConstants.VOICE_INPUT
    IMAGE = MessageConstants.IMAGE_INPUT
    MULTIMODAL = MessageConstants.MULTIMODAL_INPUT


class ProcessingType(str, Enum):
    """多模态处理类型枚举"""
    VOICE_TRANSCRIPTION = MessageConstants.VOICE_TRANSCRIPTION
    IMAGE_ANALYSIS = MessageConstants.IMAGE_ANALYSIS
    SKIN_ANALYSIS = MessageConstants.SKIN_ANALYSIS
    PRODUCT_RECOGNITION = MessageConstants.PRODUCT_RECOGNITION


class ProcessingStatus(str, Enum):
    """多模态处理状态枚举"""
    UPLOADING = MessageConstants.UPLOADING
    PROCESSING = MessageConstants.PROCESSING
    TRANSCRIBING = MessageConstants.TRANSCRIBING
    ANALYZING = MessageConstants.ANALYZING
    COMPLETED = MessageConstants.COMPLETED
    ERROR = MessageConstants.ERROR