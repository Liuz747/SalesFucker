"""
消息验证工具模块

该模块提供消息系统相关的验证函数，确保数据完整性和类型安全。

核心功能:
- 消息类型验证
- 合规状态验证  
- 市场策略验证
- 其他数据格式验证
"""

from .constants import MessageConstants, StatusConstants, WorkflowConstants


def validate_message_type(message_type: str) -> bool:
    """
    验证消息类型是否有效
    
    参数:
        message_type: 待验证的消息类型字符串
        
    返回:
        bool: 类型有效返回True，否则返回False
    """
    valid_types = [
        MessageConstants.QUERY,
        MessageConstants.RESPONSE,
        MessageConstants.NOTIFICATION,
        MessageConstants.TRIGGER,
        MessageConstants.SUGGESTION
    ]
    return message_type in valid_types


def validate_compliance_status(status: str) -> bool:
    """
    验证合规状态是否有效
    
    参数:
        status: 待验证的合规状态字符串
        
    返回:
        bool: 状态有效返回True，否则返回False
    """
    valid_statuses = [
        StatusConstants.APPROVED,
        StatusConstants.FLAGGED,
        StatusConstants.BLOCKED
    ]
    return status in valid_statuses


def validate_market_strategy(strategy: str) -> bool:
    """
    验证市场策略是否有效
    
    参数:
        strategy: 待验证的市场策略字符串
        
    返回:
        bool: 策略有效返回True，否则返回False
    """
    valid_strategies = [
        WorkflowConstants.PREMIUM_STRATEGY,
        WorkflowConstants.BUDGET_STRATEGY,
        WorkflowConstants.YOUTH_STRATEGY,
        WorkflowConstants.MATURE_STRATEGY
    ]
    return strategy in valid_strategies


def validate_input_type(input_type: str) -> bool:
    """
    验证输入类型是否有效
    
    参数:
        input_type: 待验证的输入类型字符串
        
    返回:
        bool: 类型有效返回True，否则返回False
    """
    valid_input_types = [
        MessageConstants.TEXT_INPUT,
        MessageConstants.VOICE_INPUT,
        MessageConstants.IMAGE_INPUT
    ]
    return input_type in valid_input_types 