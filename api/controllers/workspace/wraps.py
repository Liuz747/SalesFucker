"""
租户验证依赖

提供端点级别的租户验证依赖，确保安全的多租户隔离。
每个端点可以独立控制是否需要租户验证。

核心功能:
- 装饰器模式的租户验证
- Redis缓存优化的验证性能
- 细粒度的端点访问控制
"""

from typing import Optional

from fastapi import HTTPException, Request

from services.tenant_service import TenantService, TenantModel
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantValidation")


async def validate_and_get_tenant_id(request: Request) -> Optional[TenantModel]:
    """依赖注入函数 - 租户验证"""
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "TENANT_ID_REQUIRED",
                "message": "请求必须包含租户ID",
                "methods": "Header: X-Tenant-ID"
            }
        )
    
    try:
        tenant = await TenantService.query_tenant(tenant_id)
        
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
        
        return tenant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail="租户验证失败")