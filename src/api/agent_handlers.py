"""
智能体API处理器

提供智能体测试和管理的核心处理逻辑。
"""

from typing import Dict, Any
import logging

from src.agents import create_agent_set, get_orchestrator
from src.utils import get_component_logger


class AgentTestHandler:
    """智能体测试处理器"""
    
    def __init__(self):
        self.logger = get_component_logger(__name__, "AgentTestHandler")
    
    async def get_tenant_agents(self, tenant_id: str) -> Dict[str, Any]:
        """获取或创建租户的完整9智能体集合。"""
        from src.agents import agent_registry
        
        # 检查完整智能体集合是否存在（检查几个关键智能体）
        compliance_agent = agent_registry.get_agent(f"compliance_review_{tenant_id}")
        sentiment_agent = agent_registry.get_agent(f"sentiment_analysis_{tenant_id}")
        sales_agent = agent_registry.get_agent(f"sales_agent_{tenant_id}")
        
        if not all([compliance_agent, sentiment_agent, sales_agent]):
            # 如果不存在则创建完整智能体集合
            agents = create_agent_set(tenant_id)
            self.logger.info(f"为租户创建了完整的9智能体集合: {tenant_id}")
            return agents
        
        # 返回该租户的所有已注册智能体
        tenant_agents = {}
        for agent_id, agent in agent_registry.agents.items():
            if agent.tenant_id == tenant_id:
                # 从agent_id中提取智能体类型
                agent_type = agent_id.replace(f"_{tenant_id}", "").replace("_agent", "").replace("_review", "").replace("_analysis", "")
                tenant_agents[agent_type] = agent
        
        return tenant_agents
    
    async def test_compliance_agent(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试合规智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        compliance_agent = agents.get("compliance")
        
        if not compliance_agent:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="未找到合规智能体")
        
        # 测试合规检查
        result = await compliance_agent.checker.perform_compliance_check(test_message)
        
        return {
            "test_message": test_message,
            "compliance_result": result,
            "agent_id": compliance_agent.agent_id
        }
    
    async def test_sales_agent(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试销售智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        sales_agent = agents.get("sales")
        
        if not sales_agent:
            from fastapi import HTTPException
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
    
    async def test_sentiment_agent(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试情感分析智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        sentiment_agent = agents.get("sentiment")
        
        if not sentiment_agent:
            from fastapi import HTTPException
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
    
    async def test_intent_agent(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试意图分析智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        intent_agent = agents.get("intent")
        
        if not intent_agent:
            from fastapi import HTTPException
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
    
    async def test_product_agent(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试产品专家智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        product_agent = agents.get("product")
        
        if not product_agent:
            from fastapi import HTTPException
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
    
    async def test_all_agents(self, tenant_id: str, test_message: str) -> Dict[str, Any]:
        """测试所有9个智能体"""
        agents = await self.get_tenant_agents(tenant_id)
        
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