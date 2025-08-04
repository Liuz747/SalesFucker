"""
故障检测模块

负责分析异常类型和决定故障转移策略。
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .models import FailureType, FailoverAction, FailureContext, FailoverConfig
from ..base_provider import (
    BaseProvider,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError
)
from ..provider_config import ProviderType
from ..intelligent_router import RoutingContext
from src.utils import get_component_logger


class FailureDetector:
    """故障检测器"""
    
    def __init__(self, config: FailoverConfig):
        """
        初始化故障检测器
        
        参数:
            config: 故障转移配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "FailureDetector")
    
    def classify_failure(
        self, 
        error: Exception, 
        provider_type: ProviderType,
        request_id: str
    ) -> FailureType:
        """
        分类故障类型
        
        参数:
            error: 异常对象
            provider_type: 供应商类型
            request_id: 请求ID
            
        返回:
            FailureType: 故障类型
        """
        error_message = str(error).lower()
        
        # 基于异常类型进行分类
        if isinstance(error, RateLimitError):
            return FailureType.RATE_LIMIT
        elif isinstance(error, AuthenticationError):
            return FailureType.AUTHENTICATION
        elif isinstance(error, ModelNotFoundError):
            return FailureType.MODEL_NOT_FOUND
        elif isinstance(error, TimeoutError):
            return FailureType.TIMEOUT
        
        # 基于错误消息进行分类
        if any(keyword in error_message for keyword in ["timeout", "timed out"]):
            return FailureType.TIMEOUT
        elif any(keyword in error_message for keyword in ["rate limit", "quota", "too many requests"]):
            return FailureType.RATE_LIMIT
        elif any(keyword in error_message for keyword in ["unauthorized", "authentication", "invalid api key"]):
            return FailureType.AUTHENTICATION
        elif any(keyword in error_message for keyword in ["model not found", "invalid model"]):
            return FailureType.MODEL_NOT_FOUND
        elif any(keyword in error_message for keyword in ["network", "connection"]):
            return FailureType.NETWORK_ERROR
        elif any(keyword in error_message for keyword in ["quota exceeded", "billing"]):
            return FailureType.QUOTA_EXCEEDED
        else:
            return FailureType.API_ERROR
    
    def determine_failover_action(
        self, 
        failure_context: FailureContext
    ) -> FailoverAction:
        """
        决定故障转移动作
        
        参数:
            failure_context: 故障上下文
            
        返回:
            FailoverAction: 故障转移动作
        """
        failure_type = failure_context.failure_type
        attempt_count = failure_context.attempt_count
        
        # 获取故障模式配置
        pattern = self.config.failure_patterns.get(failure_type)
        if not pattern:
            # 未知故障类型，使用默认策略
            return FailoverAction.SWITCH_PROVIDER if attempt_count < 2 else FailoverAction.FAIL_FAST
        
        max_retries = pattern.get("max_retries", 0)
        switch_threshold = pattern.get("switch_threshold", 1)
        
        # 基于故障类型和尝试次数决定动作
        if failure_type in [FailureType.AUTHENTICATION, FailureType.MODEL_NOT_FOUND]:
            # 这些错误不应该重试同一供应商
            return FailoverAction.SWITCH_PROVIDER
        
        if attempt_count <= max_retries:
            return FailoverAction.RETRY_SAME
        elif attempt_count <= switch_threshold:
            return FailoverAction.SWITCH_PROVIDER
        else:
            return FailoverAction.FAIL_FAST
    
    def should_trigger_circuit_breaker(
        self, 
        failure_context: FailureContext,
        recent_failures: int
    ) -> bool:
        """
        判断是否应该触发断路器
        
        参数:
            failure_context: 故障上下文
            recent_failures: 最近失败次数
            
        返回:
            bool: 是否触发断路器
        """
        # 严重故障类型立即触发断路器
        critical_failures = [
            FailureType.AUTHENTICATION,
            FailureType.QUOTA_EXCEEDED,
            FailureType.MODEL_NOT_FOUND
        ]
        
        if failure_context.failure_type in critical_failures:
            return True
        
        # 基于失败次数判断
        return recent_failures >= self.config.circuit_breaker_threshold
    
    def extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """
        提取错误详细信息
        
        参数:
            error: 异常对象
            
        返回:
            Dict[str, Any]: 错误详细信息
        """
        details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        # 提取特定异常的额外信息
        if isinstance(error, ProviderError):
            details.update({
                "status_code": getattr(error, 'status_code', None),
                "provider_error_code": getattr(error, 'error_code', None),
                "retry_after": getattr(error, 'retry_after', None)
            })
        
        return details
    
    def create_failure_context(
        self,
        provider_type: ProviderType,
        error: Exception,
        request_id: str,
        attempt_count: int,
        original_request=None,
        routing_context=None
    ) -> FailureContext:
        """
        创建故障上下文
        
        参数:
            provider_type: 供应商类型
            error: 异常对象
            request_id: 请求ID
            attempt_count: 尝试次数
            original_request: 原始请求
            routing_context: 路由上下文
            
        返回:
            FailureContext: 故障上下文对象
        """
        failure_type = self.classify_failure(error, provider_type, request_id)
        error_details = self.extract_error_details(error)
        
        return FailureContext(
            provider_type=provider_type,
            error=error,
            failure_type=failure_type,
            request_id=request_id,
            attempt_count=attempt_count,
            original_request=original_request,
            routing_context=routing_context,
            error_details=error_details
        )