"""
Agent API Endpoints

REST API endpoints for agent interaction and testing.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from src.agents import create_agent_set, get_orchestrator, agent_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response Models
class ConversationRequest(BaseModel):
    """Request model for starting a conversation."""
    tenant_id: str = Field(description="Tenant identifier")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    message: str = Field(description="Customer message")
    input_type: str = Field("text", description="Input type (text, voice, image)")


class ConversationResponse(BaseModel):
    """Response model for conversation processing."""
    conversation_id: str
    response: str
    processing_complete: bool
    error_state: Optional[str] = None
    agent_responses: Dict[str, Any] = Field(default_factory=dict)
    compliance_status: str = Field("approved")
    human_escalation: bool = False


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    agent_id: str
    is_active: bool
    messages_processed: int
    errors: int
    last_activity: Optional[str] = None


class TenantAgentsResponse(BaseModel):
    """Response model for tenant agent listing."""
    tenant_id: str
    agents: List[AgentStatusResponse]
    total_agents: int


# Dependency to get or create agents for a tenant
async def get_tenant_agents(tenant_id: str) -> Dict[str, Any]:
    """Get or create agents for a tenant."""
    # Check if agents already exist
    compliance_agent = agent_registry.get_agent(f"compliance_review_{tenant_id}")
    sales_agent = agent_registry.get_agent(f"sales_agent_{tenant_id}")
    
    if not compliance_agent or not sales_agent:
        # Create agent set if doesn't exist
        agents = create_agent_set(tenant_id)
        logger.info(f"Created agent set for tenant: {tenant_id}")
        return agents
    
    return {
        "compliance": compliance_agent,
        "sales": sales_agent
    }


@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """
    Process a customer conversation through the multi-agent system.
    
    This endpoint orchestrates the full conversation flow:
    1. Compliance review
    2. Sentiment analysis (placeholder)
    3. Intent analysis (placeholder)
    4. Sales agent processing
    5. Response generation
    """
    try:
        # Ensure agents exist for tenant
        await get_tenant_agents(request.tenant_id)
        
        # Get orchestrator for tenant
        orchestrator = get_orchestrator(request.tenant_id)
        
        # Process conversation
        result = await orchestrator.process_conversation(
            customer_input=request.message,
            customer_id=request.customer_id,
            input_type=request.input_type
        )
        
        # Extract response from sales agent or use fallback
        final_response = result.final_response
        if not final_response and result.agent_responses.get("sales_agent_" + request.tenant_id):
            final_response = result.agent_responses[f"sales_agent_{request.tenant_id}"]["response"]
        
        if not final_response:
            final_response = "Thank you for your message! How can I help you with your beauty needs today?"
        
        return ConversationResponse(
            conversation_id=result.conversation_id,
            response=final_response,
            processing_complete=result.processing_complete,
            error_state=result.error_state,
            agent_responses=result.agent_responses,
            compliance_status=result.compliance_result.get("status", "approved"),
            human_escalation=result.human_escalation
        )
        
    except Exception as e:
        logger.error(f"Conversation processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Conversation processing failed: {str(e)}"
        )


@router.get("/tenant/{tenant_id}/status", response_model=TenantAgentsResponse)
async def get_tenant_agent_status(tenant_id: str):
    """Get status of all agents for a specific tenant."""
    try:
        # Ensure agents exist
        agents = await get_tenant_agents(tenant_id)
        
        agent_statuses = []
        for agent_name, agent in agents.items():
            if agent:
                status = AgentStatusResponse(
                    agent_id=agent.agent_id,
                    is_active=agent.is_active,
                    messages_processed=agent.processing_stats["messages_processed"],
                    errors=agent.processing_stats["errors"],
                    last_activity=agent.processing_stats["last_activity"].isoformat() 
                        if agent.processing_stats["last_activity"] else None
                )
                agent_statuses.append(status)
        
        return TenantAgentsResponse(
            tenant_id=tenant_id,
            agents=agent_statuses,
            total_agents=len(agent_statuses)
        )
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent status: {str(e)}"
        )


@router.post("/tenant/{tenant_id}/compliance/test")
async def test_compliance_agent(tenant_id: str, test_message: str):
    """Test the compliance agent with a specific message."""
    try:
        agents = await get_tenant_agents(tenant_id)
        compliance_agent = agents.get("compliance")
        
        if not compliance_agent:
            raise HTTPException(status_code=404, detail="Compliance agent not found")
        
        # Test compliance check
        result = await compliance_agent._perform_compliance_check(test_message)
        
        return {
            "test_message": test_message,
            "compliance_result": result,
            "agent_id": compliance_agent.agent_id
        }
        
    except Exception as e:
        logger.error(f"Compliance test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Compliance test failed: {str(e)}"
        )


@router.post("/tenant/{tenant_id}/sales/test")
async def test_sales_agent(tenant_id: str, test_message: str):
    """Test the sales agent with a specific message."""
    try:
        agents = await get_tenant_agents(tenant_id)
        sales_agent = agents.get("sales")
        
        if not sales_agent:
            raise HTTPException(status_code=404, detail="Sales agent not found")
        
        # Create a mock conversation state for testing
        from src.agents.core import ConversationState
        
        test_state = ConversationState(
            tenant_id=tenant_id,
            customer_input=test_message,
            compliance_result={"status": "approved"},
            intent_analysis={"market_strategy": "premium"}
        )
        
        # Process through sales agent
        result_state = await sales_agent.process_conversation(test_state)
        
        return {
            "test_message": test_message,
            "sales_response": result_state.agent_responses.get(sales_agent.agent_id, {}),
            "conversation_stage": result_state.agent_responses.get(sales_agent.agent_id, {}).get("conversation_stage"),
            "agent_id": sales_agent.agent_id
        }
        
    except Exception as e:
        logger.error(f"Sales agent test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sales agent test failed: {str(e)}"
        )


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