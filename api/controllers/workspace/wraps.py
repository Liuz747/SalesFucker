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

from fastapi import Request

from core.app import Orchestrator
from libs.exceptions import (
    BaseHTTPException,
    TenantIdRequiredException,
    TenantDisabledException,
    TenantNotFoundException,
    TenantValidationException
)
from libs.types import AccountStatus
from services.tenant_service import TenantService, TenantModel
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantValidation")


async def validate_and_get_tenant(request: Request) -> Optional[TenantModel]:
    """依赖注入函数 - 租户验证"""
    tenant_id = request.headers.get("X-Tenant-ID")

    if not tenant_id:
        raise TenantIdRequiredException()

    try:
        tenant = await TenantService.query_tenant(tenant_id)

        if not tenant:
            raise TenantNotFoundException(tenant_id)

        if tenant.status != AccountStatus.ACTIVE:
            raise TenantDisabledException(tenant_id)

        return tenant

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
        raise TenantValidationException(tenant_id, str(e))


async def get_orchestrator(request: Request):
    """
    Lazy loading（并缓存）编排器实例。
    - 仅在首次被工作流端点请求时创建
    - 实例存放于 app.state，供后续请求复用
    """
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        orchestrator = Orchestrator()
        request.app.state.orchestrator = orchestrator
    try:
        yield orchestrator
    finally:
        pass
