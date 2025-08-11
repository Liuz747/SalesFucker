"""
智能体相关依赖
"""

from fastapi import HTTPException, Depends

from src.auth import JWTTenantContext, get_jwt_tenant_context
from src.agents.base.registry import AgentRegistry
from src.agents.base.registry import agent_registry as global_registry


async def get_agent_registry_service() -> AgentRegistry:
    """返回全局智能体注册中心"""
    return global_registry


async def validate_agent_id(
    agent_id: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry: AgentRegistry = Depends(get_agent_registry_service),
) -> str:
    """校验智能体归属与存在性"""
    if not tenant_context.can_access_agent(agent_id):
        raise HTTPException(status_code=403, detail={"error": "AGENT_ACCESS_DENIED", "message": f"租户无权访问智能体 {agent_id}"})

    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail={"error": "AGENT_NOT_FOUND", "message": f"智能体 {agent_id} 不存在"})

    if agent.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=403, detail={"error": "AGENT_ACCESS_DENIED", "message": "智能体不属于当前租户"})

    return agent_id


