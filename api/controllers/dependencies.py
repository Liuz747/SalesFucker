from typing import Any
from fastapi import HTTPException, Request

from utils import get_component_logger
from core.app.orchestrator import get_orchestrator

logger = get_component_logger(__name__, "OrchestratorDep")


def get_orchestrator_service(tenant_id: str):
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


# === 已废弃 ===
async def get_request_context(request: Request) -> dict[str, Any]:
    """返回请求上下文（租户、UA等）"""
    return {
        "tenant_id": request.state.tenant_id,
    }


