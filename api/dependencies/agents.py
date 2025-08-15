"""
智能体相关依赖
"""

from fastapi import HTTPException, Depends

from infra.auth.jwt_auth import get_service_context
from infra.auth.models import ServiceContext
from src.agents.base.registry import AgentRegistry
from src.agents.base.registry import agent_registry as global_registry


async def get_agent_registry_service() -> AgentRegistry:
    """返回全局智能体注册中心"""
    return global_registry


async def validate_agent_id(
    agent_id: str,
    service: ServiceContext = Depends(get_service_context),
    registry: AgentRegistry = Depends(get_agent_registry_service),
) -> str:
    """校验智能体归属与存在性"""
    # In trust model, backend service manages all agent access
    # Agent access validation will be implemented in future versions

    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail={"error": "AGENT_NOT_FOUND", "message": f"智能体 {agent_id} 不存在"})

    # Note: tenant_id validation will be added when request context includes tenant_id
    # if agent.tenant_id != request.tenant_id:
        raise HTTPException(status_code=403, detail={"error": "AGENT_ACCESS_DENIED", "message": "智能体不属于当前租户"})

    return agent_id


