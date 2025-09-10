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
from contextlib import asynccontextmanager
from collections.abc import Callable

from fastapi import HTTPException, Request, Depends

from services.tenant_service import TenantService
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantValidation")


def tenant_validation():
    """
    租户验证装饰器
    
    使用方法:
        @tenant_validation()
        async def my_endpoint(request: Request, tenant_id: str, ...):
            # tenant对象已验证并注入
            pass
    """
    def decorator(process: Callable) -> Callable:
        @wraps(process)
        async def wrapper(*args, request: Request = Depends(), **kwargs):
            # 直接从请求中提取租户ID
            tenant_id = request.headers.get("X-Tenant-ID")

            if not tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Tenant_ID_Required",
                        "message": "请求必须包含租户ID",
                        "methods": "Header: X-Tenant-ID"
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
                            "error": "Tenant_Not_Found",
                            "message": f"租户 {tenant_id} 不存在"
                        }
                    )
                
                if not tenant.is_active:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "Tenant_Disabled", 
                            "message": f"租户 {tenant_id} 已被禁用"
                        }
                    )
                
                # 注入验证后的租户ID
                kwargs["tenant_id"] = tenant_id
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
                raise HTTPException(status_code=500, detail="租户验证失败")
            finally:
                await service.cleanup()
            
            return await process(*args, **kwargs)
        
        return wrapper
    return decorator


@asynccontextmanager
async def tenant_validation_context():
    service = TenantService()
    try:
        await service.dispatch()
        yield service
    finally:
        await service.cleanup()


async def validate_and_get_tenant_id(request: Request) -> str:
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Tenant_ID_Required",
                "message": "请求必须包含租户ID",
                "methods": "Header: X-Tenant-ID"
            }
        )
    # 验证租户
    async with tenant_validation_context() as service:
        try:
            tenant = await service.query_tenant(tenant_id)
            
            if not tenant:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Tenant_Not_Found",
                        "message": f"租户 {tenant_id} 不存在"
                    }
                )
            
            if not tenant.is_active:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Tenant_Disabled", 
                        "message": f"租户 {tenant_id} 已被禁用"
                    }
                )
            
            # 注入验证后的租户ID
            return tenant_id
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
            raise HTTPException(status_code=500, detail="租户验证失败")