"""
编排器服务依赖
"""

from fastapi import HTTPException, Depends

from src.auth import JWTTenantContext, get_jwt_tenant_context
from src.utils import get_component_logger
from src.core.orchestrator import get_orchestrator

logger = get_component_logger(__name__, "OrchestratorDep")


async def get_orchestrator_service(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """获取租户编排器实例"""
    try:
        return get_orchestrator(tenant_context.tenant_id)
    except Exception as e:
        logger.error(f"获取编排器失败，租户: {tenant_context.tenant_id}, 错误: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "ORCHESTRATOR_UNAVAILABLE", "message": "编排器服务暂时不可用"},
        )


