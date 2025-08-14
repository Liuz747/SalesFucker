"""
系统工具模块

该包提供多智能体系统的通用工具函数和混入类。
消除代码重复，提供一致的功能接口。

模块组织:
- time_utils: 时间处理工具
- logger_utils: 日志工具
- status_mixin: 状态管理混入
- error_handling: 错误处理装饰器
- validation: 数据验证工具

注意: 类型定义、常量和性能配置已移至 src/libs/ 目录
"""

from .time_utils import get_current_datetime, get_processing_time_ms, format_timestamp, format_datatime
from .logger_utils import get_component_logger, LoggerMixin
from .status_mixin import StatusMixin
from .error_handling import with_error_handling, with_fallback, ErrorHandler
from .validation import (
    validate_message_type,
    validate_compliance_status,
    validate_market_strategy,
    validate_input_type
)
from .response_parser import (
    parse_structured_response,
    parse_compliance_response,
    parse_sentiment_response,
    parse_intent_response
)

__all__ = [
    # 时间工具
    "get_current_datetime",
    "get_processing_time_ms", 
    "format_timestamp",
    "format_datatime",
    # 日志工具
    "get_component_logger",
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
    
    # 响应解析工具
    "parse_structured_response",
    "parse_compliance_response",
    "parse_sentiment_response",
    "parse_intent_response"
] 