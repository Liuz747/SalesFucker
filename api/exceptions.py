"""
API异常处理模块

该模块定义了API层的自定义异常类，提供标准化的错误响应格式。

核心功能:
- 统一异常格式
- 错误代码标准化
- 多语言错误消息支持
- 异常链追踪
"""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException


class APIException(Exception):
    """
    API基础异常类
    
    提供标准化的API错误响应格式，包含错误代码、消息、详细信息和时间戳。
    """
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        初始化API异常
        
        参数:
            status_code: HTTP状态码
            error_code: 业务错误代码
            message: 错误消息
            details: 详细错误信息
            original_exception: 原始异常（用于异常链）
        """
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        
        super().__init__(message)


class ValidationException(APIException):
    """请求参数验证异常"""
    
    def __init__(self, message: str = "请求参数验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details
        )


class AgentNotFoundException(APIException):
    """智能体未找到异常"""
    
    def __init__(self, agent_id: str):
        super().__init__(
            status_code=404,
            error_code="AGENT_NOT_FOUND",
            message=f"智能体 {agent_id} 不存在",
            details={"agent_id": agent_id}
        )


class AgentUnavailableException(APIException):
    """智能体不可用异常"""
    
    def __init__(self, agent_id: str, reason: str = "智能体服务暂时不可用"):
        super().__init__(
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
            message=reason,
            details={"agent_id": agent_id}
        )


class TenantAccessDeniedException(APIException):
    """租户访问拒绝异常"""
    
    def __init__(self, tenant_id: str, resource: str = "资源"):
        super().__init__(
            status_code=403,
            error_code="TENANT_ACCESS_DENIED",
            message=f"租户 {tenant_id} 无权访问{resource}",
            details={"tenant_id": tenant_id, "resource": resource}
        )


class LLMProviderException(APIException):
    """LLM提供商异常"""
    
    def __init__(self, provider_name: str, message: str = "LLM提供商服务异常"):
        super().__init__(
            status_code=502,
            error_code="LLM_PROVIDER_ERROR",
            message=message,
            details={"provider": provider_name}
        )


class ConversationException(APIException):
    """对话处理异常"""
    
    def __init__(self, message: str = "对话处理失败", thread_id: Optional[str] = None):
        details = {}
        if thread_id:
            details["thread_id"] = thread_id
            
        super().__init__(
            status_code=500,
            error_code="CONVERSATION_ERROR",
            message=message,
            details=details
        )


class ProcessingException(APIException):
    """处理异常"""
    
    def __init__(self, message: str = "处理失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=500,
            error_code="PROCESSING_ERROR",
            message=message,
            details=details or {}
        )


class MultimodalProcessingException(APIException):
    """多模态处理异常"""
    
    def __init__(self, processing_type: str, message: str = "多模态处理失败"):
        super().__init__(
            status_code=500,
            error_code="MULTIMODAL_PROCESSING_ERROR",
            message=message,
            details={"processing_type": processing_type}
        )


class RateLimitExceededException(APIException):
    """速率限制超出异常"""
    
    def __init__(self, limit: int, window_seconds: int):
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=f"请求频率超限：{limit}次/{window_seconds}秒",
            details={"limit": limit, "window_seconds": window_seconds}
        )


class SafetyViolationException(APIException):
    """安全策略违规异常"""
    
    def __init__(self, violation_type: str, message: str = "内容违反安全策略"):
        super().__init__(
            status_code=400,
            error_code="SAFETY_VIOLATION",
            message=message,
            details={"violation_type": violation_type}
        )


class SystemMaintenanceException(APIException):
    """系统维护异常"""
    
    def __init__(self, estimated_restore_time: Optional[str] = None):
        message = "系统正在维护中"
        if estimated_restore_time:
            message += f"，预计恢复时间：{estimated_restore_time}"
            
        super().__init__(
            status_code=503,
            error_code="SYSTEM_MAINTENANCE",
            message=message,
            details={"estimated_restore_time": estimated_restore_time}
        )


# 异常映射字典，用于将内部异常转换为API异常
EXCEPTION_MAPPING = {
    "AgentNotFound": AgentNotFoundException,
    "AgentUnavailable": AgentUnavailableException,
    "TenantAccessDenied": TenantAccessDeniedException,
    "LLMProviderError": LLMProviderException,
    "ConversationError": ConversationException,
    "MultimodalProcessingError": MultimodalProcessingException,
    "RateLimitExceeded": RateLimitExceededException,
    "SafetyViolation": SafetyViolationException,
    "SystemMaintenance": SystemMaintenanceException,
}


def map_internal_exception(exc: Exception) -> APIException:
    """
    将内部异常映射为API异常
    
    参数:
        exc: 内部异常
        
    返回:
        APIException: 对应的API异常
    """
    exc_name = exc.__class__.__name__
    
    if exc_name in EXCEPTION_MAPPING:
        exception_class = EXCEPTION_MAPPING[exc_name]
        # 尝试从原始异常中提取参数
        if hasattr(exc, 'args') and exc.args:
            return exception_class(exc.args[0])
        else:
            return exception_class()
    
    # 默认返回通用API异常
    return APIException(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="服务器内部错误",
        original_exception=exc
    )