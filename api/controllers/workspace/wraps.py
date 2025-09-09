"""
租户验证装饰器

提供端点级别的租户验证装饰器，确保安全的多租户隔离。
每个端点可以独立控制是否需要租户验证。

核心功能:
- 装饰器模式的租户验证
- Redis缓存优化的验证性能
- 细粒度的端点访问控制
"""

from functools import wraps
from typing import Optional
from collections.abc import Callable

from fastapi import HTTPException, Request

from services.tenant_service import TenantService
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantValidation")


def _extract_tenant_id(request: Request) -> Optional[str]:
    """
    从请求中提取租户ID
    
    支持多种提取方式：
    1. Header: X-Tenant-ID
    2. 路径参数: /tenants/{tenant_id}/...
    
    参数:
        request: HTTP请求
        
    返回:
        Optional[str]: 租户ID
    """
    # 方式1: 从Header获取 (推荐)
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    
    # 方式2: 从路径参数获取
    path_parts = request.url.path.split("/")
    if "tenants" in path_parts:
        try:
            tenant_index = path_parts.index("tenants")
            if tenant_index + 1 < len(path_parts):
                return path_parts[tenant_index + 1]
        except (ValueError, IndexError):
            pass
    
    return None


def tenant_validation():
    """
    租户验证装饰器
    
    使用方法:
        @tenant_validation()
        async def my_endpoint(request: Request, tenant: TenantOrm, ...):
            # tenant对象已验证并注入
            pass
    """
    def decorator(process: Callable) -> Callable:
        @wraps(process)
        async def wrapper(*args, **kwargs):
            # 从参数中找到 Request 对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=500, 
                    detail="Request object not found"
                )
            
            # 直接从请求中提取租户ID
            tenant_id = _extract_tenant_id(request)
            if not tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "TENANT_ID_REQUIRED",
                        "message": "请求必须包含租户ID",
                        "methods": [
                            "Header: X-Tenant-ID (推荐)",
                            "路径参数: /tenants/{tenant_id}/..."
                        ]
                    }
                )
            
            # 验证租户
            try:
                service = TenantService()
                await service.dispatch()
                tenant = await service.query_tenant(tenant_id)
                
                if not tenant:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "TENANT_NOT_FOUND",
                            "message": f"租户 {tenant_id} 不存在"
                        }
                    )
                
                if not tenant.is_active:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "TENANT_DISABLED", 
                            "message": f"租户 {tenant_id} 已被禁用"
                        }
                    )
                
                # 注入验证后的租户对象
                kwargs["tenant"] = tenant
                kwargs["tenant_id"] = tenant_id
                
                await service.cleanup()
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
                raise HTTPException(status_code=500, detail="租户验证失败")
            
            return await process(*args, **kwargs)
        
        return wrapper
    return decorator
