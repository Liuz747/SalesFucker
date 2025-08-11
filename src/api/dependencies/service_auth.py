"""
服务间认证依赖模块

提供服务间JWT认证的FastAPI依赖函数，
用于验证Backend服务向MAS系统的API调用权限。
"""

from fastapi import Depends
from src.auth.jwt_auth import get_service_context, require_service_scopes
from src.auth.models import ServiceContext

# 基础服务认证依赖
ServiceAuth = Depends(get_service_context)

# 管理员权限依赖
ServiceAdminAuth = require_service_scopes("backend:admin")

# 便捷别名
get_service_auth = get_service_context
require_admin_scope = require_service_scopes("backend:admin")


def get_authenticated_service() -> ServiceContext:
    """
    获取已认证的服务上下文
    
    这是一个便捷的依赖函数，用于需要服务认证但不需要特定权限的端点。
    
    返回:
        ServiceContext: 认证成功的服务上下文
    """
    return Depends(get_service_context)


def require_service_admin() -> ServiceContext:
    """
    要求具有管理员权限的服务认证
    
    这是一个便捷的依赖函数，用于需要管理员权限的端点。
    
    返回:
        ServiceContext: 具有管理员权限的服务上下文
    """
    return require_service_scopes("backend:admin")