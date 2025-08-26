"""
编排器服务依赖
"""

from fastapi import HTTPException, Depends

from infra.auth.jwt_auth import get_service_context
from infra.auth.jwt_auth import ServiceContext
from utils import get_component_logger
from src.core.orchestrator import get_orchestrator

logger = get_component_logger(__name__, "OrchestratorDep")


def get_orchestrator_for_tenant(tenant_id: str):
    """获取指定租户的编排器实例"""
    try:
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail={"error": "MISSING_TENANT_ID", "message": "Tenant ID is required"}
            )
        return get_orchestrator(tenant_id)
    except Exception as e:
        logger.error(f"获取编排器失败，错误: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "ORCHESTRATOR_UNAVAILABLE", "message": "编排器服务暂时不可用"},
        )


async def get_orchestrator_service(
    service: ServiceContext = Depends(get_service_context)
):
    """验证服务权限，返回编排器工厂函数"""
    # 只验证服务权限，不获取具体的编排器实例
    # 编排器实例需要在业务逻辑中根据tenant_id获取
    return get_orchestrator_for_tenant


