"""
编排器服务依赖
"""

from fastapi import HTTPException, Depends

from infra.auth.jwt_auth import get_service_context
from infra.auth.jwt_auth import ServiceContext
from utils import get_component_logger
from src.core.orchestrator import get_orchestrator

logger = get_component_logger(__name__, "OrchestratorDep")


async def get_orchestrator_service(
    service: ServiceContext = Depends(get_service_context)
):
    """获取租户编排器实例"""
    try:
        # Extract tenant_id from service context
        if not service.tenant_id:
            raise HTTPException(
                status_code=400,
                detail={"error": "MISSING_TENANT_ID", "message": "Tenant ID is required"}
            )
        return get_orchestrator(service.tenant_id)
    except Exception as e:
        logger.error(f"获取编排器失败，错误: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "ORCHESTRATOR_UNAVAILABLE", "message": "编排器服务暂时不可用"},
        )


