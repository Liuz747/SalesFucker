"""
智能体API端点处理器

将主要的智能体测试端点分离到独立模块，保持代码组织清晰。
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from src.agents import get_orchestrator, agent_registry
from src.api.agent_handlers import AgentTestHandler
from src.utils import get_component_logger


logger = get_component_logger(__name__, "AgentEndpoints")

# 创建路由器
router = APIRouter(prefix="/agents", tags=["agents"])

# 创建测试处理器
test_handler = AgentTestHandler()


@router.post("/tenant/{tenant_id}/compliance/test")
async def test_compliance_agent(tenant_id: str, test_message: str):
    """使用特定消息测试合规智能体。"""
    try:
        return await test_handler.test_compliance_agent(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"合规测试失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"合规测试失败: {str(e)}"
        )


@router.post("/tenant/{tenant_id}/sales/test")
async def test_sales_agent(tenant_id: str, test_message: str):
    """Test the enhanced LLM-powered sales agent with a specific message."""
    try:
        return await test_handler.test_sales_agent(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"Sales agent test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sales agent test failed: {str(e)}"
        )


@router.post("/tenant/{tenant_id}/sentiment/test")
async def test_sentiment_agent(tenant_id: str, test_message: str):
    """Test the LLM-powered sentiment analysis agent."""
    try:
        return await test_handler.test_sentiment_agent(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"Sentiment agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sentiment agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/intent/test")
async def test_intent_agent(tenant_id: str, test_message: str):
    """Test the enhanced LLM-powered intent analysis agent with field extraction."""
    try:
        return await test_handler.test_intent_agent(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"Intent agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Intent agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/product/test")
async def test_product_agent(tenant_id: str, test_message: str):
    """Test the AI-powered product expert agent."""
    try:
        return await test_handler.test_product_agent(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"Product agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Product agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/agents/test-all")
async def test_all_agents(tenant_id: str, test_message: str = "I have oily skin and need a good cleanser for my daily routine."):
    """Test all 9 agents with a single message to show complete system capability."""
    try:
        return await test_handler.test_all_agents(tenant_id, test_message)
        
    except Exception as e:
        logger.error(f"All agents test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"All agents test failed: {str(e)}")


@router.get("/registry/status")
async def get_registry_status():
    """Get status of the global agent registry."""
    try:
        registered_agents = list(agent_registry.agents.keys())
        
        agent_details = []
        for agent_id, agent in agent_registry.agents.items():
            agent_details.append({
                "agent_id": agent_id,
                "tenant_id": agent.tenant_id,
                "is_active": agent.is_active,
                "messages_processed": agent.processing_stats["messages_processed"],
                "errors": agent.processing_stats["errors"]
            })
        
        return {
            "total_registered_agents": len(registered_agents),
            "registered_agent_ids": registered_agents,
            "agent_details": agent_details
        }
        
    except Exception as e:
        logger.error(f"Registry status failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Registry status failed: {str(e)}"
        )


@router.delete("/tenant/{tenant_id}/agents")
async def cleanup_tenant_agents(tenant_id: str):
    """Cleanup agents for a specific tenant (for testing)."""
    try:
        agents_to_remove = [
            agent_id for agent_id in agent_registry.agents.keys()
            if agent_id.endswith(f"_{tenant_id}")
        ]
        
        for agent_id in agents_to_remove:
            del agent_registry.agents[agent_id]
        
        return {
            "message": f"Cleaned up {len(agents_to_remove)} agents for tenant {tenant_id}",
            "removed_agents": agents_to_remove
        }
        
    except Exception as e:
        logger.error(f"Agent cleanup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent cleanup failed: {str(e)}"
        )