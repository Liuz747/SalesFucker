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
    """Get or create complete 9-agent set for a tenant."""
    # Check if full agent set exists (check a few key agents)
    compliance_agent = agent_registry.get_agent(f"compliance_review_{tenant_id}")
    sentiment_agent = agent_registry.get_agent(f"sentiment_analysis_{tenant_id}")
    sales_agent = agent_registry.get_agent(f"sales_agent_{tenant_id}")
    
    if not all([compliance_agent, sentiment_agent, sales_agent]):
        # Create complete agent set if doesn't exist
        agents = create_agent_set(tenant_id)
        logger.info(f"Created complete 9-agent set for tenant: {tenant_id}")
        return agents
    
    # Return all registered agents for this tenant
    tenant_agents = {}
    for agent_id, agent in agent_registry.agents.items():
        if agent.tenant_id == tenant_id:
            # Extract agent type from agent_id (e.g., "sales_agent_tenant1" -> "sales")
            agent_type = agent_id.replace(f"_{tenant_id}", "").replace("_agent", "").replace("_review", "").replace("_analysis", "")
            tenant_agents[agent_type] = agent
    
    return tenant_agents


@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """
    Process a customer conversation through the complete 9-agent multi-agent system.
    
    This endpoint orchestrates the full LLM-powered conversation flow:
    1. ComplianceAgent: LLM+rule hybrid safety validation
    2. SentimentAnalysisAgent: AI emotion detection and satisfaction scoring
    3. IntentAnalysisAgent: AI intent classification with field extraction
    4. SalesAgent: Dynamic LLM personalized responses
    5. ProductExpertAgent: AI product recommendations
    6. MemoryAgent: Customer profile management and persistence
    7. MarketStrategyCoordinator: Segment-based strategy selection
    8. ProactiveAgent: Behavior-triggered opportunity identification
    9. AISuggestionAgent: Human-AI collaboration and escalation decisions
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
        result = await compliance_agent.checker.perform_compliance_check(test_message)
        
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
    """Test the enhanced LLM-powered sales agent with a specific message."""
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
            intent_analysis={
                "intent": "product_inquiry",
                "conversation_stage": "consultation",
                "customer_profile": {
                    "skin_concerns": ["dryness", "sensitivity"],
                    "urgency": "medium",
                    "experience_level": "intermediate"
                }
            }
        )
        
        # Process through sales agent
        result_state = await sales_agent.process_conversation(test_state)
        
        return {
            "test_message": test_message,
            "sales_response": result_state.sales_response,
            "agent_responses": result_state.agent_responses.get(sales_agent.agent_id, {}),
            "agent_id": sales_agent.agent_id,
            "llm_powered": True
        }
        
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
        agents = await get_tenant_agents(tenant_id)
        sentiment_agent = agents.get("sentiment")
        
        if not sentiment_agent:
            raise HTTPException(status_code=404, detail="Sentiment agent not found")
        
        from src.agents.core import ConversationState
        
        test_state = ConversationState(
            tenant_id=tenant_id,
            customer_input=test_message
        )
        
        result_state = await sentiment_agent.process_conversation(test_state)
        
        return {
            "test_message": test_message,
            "sentiment_analysis": result_state.sentiment_analysis,
            "agent_id": sentiment_agent.agent_id,
            "llm_powered": True
        }
        
    except Exception as e:
        logger.error(f"Sentiment agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sentiment agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/intent/test")
async def test_intent_agent(tenant_id: str, test_message: str):
    """Test the enhanced LLM-powered intent analysis agent with field extraction."""
    try:
        agents = await get_tenant_agents(tenant_id)
        intent_agent = agents.get("intent")
        
        if not intent_agent:
            raise HTTPException(status_code=404, detail="Intent agent not found")
        
        from src.agents.core import ConversationState
        
        test_state = ConversationState(
            tenant_id=tenant_id,
            customer_input=test_message
        )
        
        result_state = await intent_agent.process_conversation(test_state)
        
        return {
            "test_message": test_message,
            "intent_analysis": result_state.intent_analysis,
            "customer_profile_extracted": result_state.intent_analysis.get("customer_profile", {}),
            "agent_id": intent_agent.agent_id,
            "llm_powered": True,
            "field_extraction": True
        }
        
    except Exception as e:
        logger.error(f"Intent agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Intent agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/product/test")
async def test_product_agent(tenant_id: str, test_message: str):
    """Test the AI-powered product expert agent."""
    try:
        agents = await get_tenant_agents(tenant_id)
        product_agent = agents.get("product")
        
        if not product_agent:
            raise HTTPException(status_code=404, detail="Product agent not found")
        
        from src.agents.core import ConversationState
        
        test_state = ConversationState(
            tenant_id=tenant_id,
            customer_input=test_message,
            customer_profile={
                "skin_type": "combination",
                "budget_preference": "medium",
                "experience_level": "intermediate"
            }
        )
        
        result_state = await product_agent.process_conversation(test_state)
        
        return {
            "test_message": test_message,
            "product_recommendations": result_state.agent_responses.get(product_agent.agent_id, {}).get("product_recommendations", {}),
            "agent_id": product_agent.agent_id,
            "llm_powered": True
        }
        
    except Exception as e:
        logger.error(f"Product agent test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Product agent test failed: {str(e)}")


@router.post("/tenant/{tenant_id}/agents/test-all")
async def test_all_agents(tenant_id: str, test_message: str = "I have oily skin and need a good cleanser for my daily routine."):
    """Test all 9 agents with a single message to show complete system capability."""
    try:
        agents = await get_tenant_agents(tenant_id)
        
        # Get orchestrator and process complete conversation
        orchestrator = get_orchestrator(tenant_id)
        result = await orchestrator.process_conversation(
            customer_input=test_message,
            customer_id="test_customer_all_agents"
        )
        
        # Extract responses from all agents
        agent_results = {}
        for agent_type, agent in agents.items():
            agent_response = result.agent_responses.get(agent.agent_id, {})
            agent_results[agent_type] = {
                "agent_id": agent.agent_id,
                "response": agent_response,
                "active": agent.agent_id in result.active_agents
            }
        
        return {
            "test_message": test_message,
            "conversation_id": result.conversation_id,
            "processing_complete": result.processing_complete,
            "final_response": result.final_response,
            "compliance_status": result.compliance_result.get("status", "unknown"),
            "human_escalation": result.human_escalation,
            "total_agents_active": len(result.active_agents),
            "agent_results": agent_results,
            "system_status": "9_agent_llm_powered_system_operational"
        }
        
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