"""
系统工具模块

该包提供多智能体系统的通用工具函数和混入类。
消除代码重复，提供一致的功能接口。

模块组织:
- time_utils: 时间处理工具
- logger_factory: 日志工厂
- status_mixin: 状态管理混入
- error_handling: 错误处理装饰器
- constants: 系统常量
"""

from .time_utils import get_current_timestamp, get_processing_time_ms, TimestampMixin
from .logger_factory import get_component_logger, LoggerMixin
from .status_mixin import StatusMixin
from .error_handling import with_error_handling, with_fallback, ErrorHandler
from .constants import (
    StatusConstants, 
    ProcessingConstants, 
    MessageConstants, 
    WorkflowConstants,
    AgentConstants,
    ErrorConstants,
    ConfigConstants
)

__all__ = [
    # 时间工具
    "get_current_timestamp",
    "get_processing_time_ms", 
    "TimestampMixin",
    
    # 日志工具
    "get_component_logger",
    "LoggerMixin",
    
    # 状态管理
    "StatusMixin",
    
    # 错误处理
    "with_error_handling",
    "with_fallback",
    "ErrorHandler",
    
    # 常量
    "StatusConstants",
    "ProcessingConstants", 
    "MessageConstants",
    "WorkflowConstants",
    "AgentConstants",
    "ErrorConstants",
    "ConfigConstants"
] 