"""
故障转移系统数据模型

定义故障转移相关的数据结构和枚举类型。
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..base_provider import LLMRequest
from ..intelligent_router import RoutingContext
from ..provider_config import ProviderType


class FailureType(str, Enum):
    """故障类型枚举"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    MODEL_NOT_FOUND = "model_not_found"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN = "unknown"


class FailoverAction(str, Enum):
    """故障转移动作枚举"""
    RETRY_SAME = "retry_same"           # 同供应商重试
    SWITCH_PROVIDER = "switch_provider"  # 切换供应商
    CIRCUIT_BREAK = "circuit_break"     # 断路器保护
    FAIL_FAST = "fail_fast"            # 快速失败


@dataclass
class FailureContext:
    """故障上下文信息"""
    provider_type: ProviderType
    error: Exception
    failure_type: FailureType
    request_id: str
    attempt_count: int = 1
    original_request: Optional[LLMRequest] = None
    routing_context: Optional[RoutingContext] = None
    timestamp: datetime = field(default_factory=datetime.now)
    error_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """断路器状态"""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None
    success_count_after_half_open: int = 0


@dataclass
class FailoverConfig:
    """故障转移配置"""
    max_retry_attempts: int = 3
    retry_delays: list = field(default_factory=lambda: [1, 2, 4])
    context_preservation_enabled: bool = True
    
    # 断路器配置
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300
    circuit_breaker_recovery_success_count: int = 3
    
    # 故障历史配置
    max_failure_history: int = 10000
    
    # 故障模式配置
    failure_patterns: Dict[FailureType, Dict[str, Any]] = field(default_factory=lambda: {
        FailureType.RATE_LIMIT: {
            "retry_delay": 60,
            "max_retries": 2,
            "switch_threshold": 2
        },
        FailureType.TIMEOUT: {
            "retry_delay": 5,
            "max_retries": 2,
            "switch_threshold": 3
        },
        FailureType.AUTHENTICATION: {
            "retry_delay": 0,
            "max_retries": 0,
            "switch_threshold": 1
        },
        FailureType.MODEL_NOT_FOUND: {
            "retry_delay": 0,
            "max_retries": 0,
            "switch_threshold": 1
        },
        FailureType.API_ERROR: {
            "retry_delay": 2,
            "max_retries": 3,
            "switch_threshold": 2
        }
    })