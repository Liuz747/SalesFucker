"""
系统工具模块

该包提供多智能体系统的通用工具函数和混入类。
消除代码重复，提供一致的功能接口。

模块组织:
- time_utils: 时间处理工具
- logger_factory: 日志工厂
- status_mixin: 状态管理混入
- error_handling: 错误处理装饰器
- validation: 数据验证工具
- types: 类型定义和枚举
- constants: 系统常量
"""

from .time_utils import get_current_datetime, get_processing_time_ms, format_timestamp
from .logger_factory import get_component_logger, LoggerMixin

# 为了向后兼容，提供get_logger函数
def get_logger(component_name: str = None):
    """获取日志器的便捷函数"""
    if component_name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            component_name = frame.f_back.f_globals.get('__name__', 'unknown')
    return get_component_logger(component_name)
from .status_mixin import StatusMixin
from .error_handling import with_error_handling, with_fallback, ErrorHandler
from .validation import (
    validate_message_type,
    validate_compliance_status,
    validate_market_strategy,
    validate_input_type
)
from .types import (
    MessageType,
    ComplianceStatus,
    MarketStrategy,
    PriorityLevel,
    InputType,
    ProcessingType,
    ProcessingStatus
)
from .constants import (
    StatusConstants, 
    ProcessingConstants, 
    MessageConstants, 
    WorkflowConstants,
    AgentConstants,
    ErrorConstants,
    ConfigConstants,
    MultiModalConstants
)

__all__ = [
    # 时间工具
    "get_current_datetime",
    "get_processing_time_ms", 
    "format_timestamp",
    
    # 日志工具
    "get_component_logger",
    "get_logger",
    "LoggerMixin",
    
    # 状态管理
    "StatusMixin",
    
    # 错误处理
    "with_error_handling",
    "with_fallback",
    "ErrorHandler",
    
    # 验证工具
    "validate_message_type",
    "validate_compliance_status",
    "validate_market_strategy",
    "validate_input_type",
    
    # 类型定义
    "MessageType",
    "ComplianceStatus", 
    "MarketStrategy",
    "PriorityLevel",
    "InputType",
    "ProcessingType",
    "ProcessingStatus",
    
    # 常量
    "StatusConstants",
    "ProcessingConstants", 
    "MessageConstants",
    "WorkflowConstants",
    "AgentConstants",
    "ErrorConstants",
    "ConfigConstants",
    "MultiModalConstants"
] 