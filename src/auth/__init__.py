"""
JWT认证模块

该模块提供基于JWT的安全认证系统，支持多租户架构和RSA-256签名验证。

核心组件:
- JWTTenantContext: JWT验证后的租户上下文
- TenantConfig: 租户配置管理
- jwt_auth: JWT验证中间件
- tenant_manager: 租户配置和密钥管理
"""

from .models import JWTTenantContext, TenantConfig, ServiceContext
from .jwt_auth import (
    get_jwt_tenant_context,
    verify_jwt_token,
    JWTVerificationError,
    TenantAccessError,
    get_service_context
)
from .tenant_manager import TenantManager, get_tenant_manager

__all__ = [
    "JWTTenantContext",
    "TenantConfig", 
    "get_jwt_tenant_context",
    "verify_jwt_token",
    "JWTVerificationError",
    "TenantAccessError",
    "TenantManager",
    "get_tenant_manager",
    "ServiceContext",
    "get_service_context"
]