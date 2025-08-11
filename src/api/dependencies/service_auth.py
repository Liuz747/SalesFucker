"""
服务间认证依赖模块

提供服务间JWT认证的FastAPI依赖函数，
用于验证Backend服务向MAS系统的API调用权限。

使用方法:
    # 基础服务认证（任何有效的服务JWT）
    @router.get("/status")
    async def get_status(service: ServiceContext = ServiceAuth):
        return {"service": service.sub}
    
    # 需要管理员权限的服务认证
    @router.post("/admin-action") 
    async def admin_action(service: ServiceContext = ServiceAdminAuth):
        return {"admin": service.is_admin()}
"""

from fastapi import Depends
from src.auth.jwt_auth import get_service_context, require_service_scopes

ServiceAuth = Depends(get_service_context)
ServiceAdminAuth = require_service_scopes("backend:admin")