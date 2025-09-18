"""
JWT认证模块

该模块提供基于JWT的安全认证系统，支持多租户架构和RSA-256签名验证。

核心组件:
- ServiceContext: JWT验证后的租户上下文
- jwt_auth: JWT验证中间件
"""

from .jwt_auth import ServiceContext, get_service_context, require_service_scopes
from .key_manager import key_manager

__all__ = [
    "ServiceContext",
    "get_service_context",
    "require_service_scopes",
    
    "key_manager"
]