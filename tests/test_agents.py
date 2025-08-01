"""
增强的LLM驱动多智能体系统测试

完整的9智能体LLM驱动系统的综合测试。
测试包括所有智能体、LLM集成和端到端工作流。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.agents.core import ConversationState, AgentMessage
from src.agents.compliance import ComplianceAgent, ComplianceRule
from src.agents.sales import SalesAgent
from src.agents.sentiment import SentimentAnalysisAgent
from src.agents.intent import IntentAnalysisAgent
from src.agents.product import ProductExpertAgent
from src.agents.memory import MemoryAgent
from src.agents.strategy import MarketStrategyCoordinator
from src.agents.proactive import ProactiveAgent
from src.agents.suggestion import AISuggestionAgent
from src.agents import create_agent_set, get_orchestrator, agent_registry


class TestComplianceAgent:
    """合规智能体测试套件。"""
    
    @pytest.fixture
    def compliance_agent(self):
        """创建测试用合规智能体。"""
        return ComplianceAgent("test_tenant")
    
    @pytest.mark.asyncio
    async def test_compliance_approved_message(self, compliance_agent):
        """测试干净的消息会被增强的LLM+规则系统批准。"""
        with patch.object(compliance_agent, '_llm_compliance_analysis', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "status": "approved",
                "violations": [],
                "severity": "low",
                "user_message": "",
                "recommended_action": "proceed"
            }
            
            result = await compliance_agent._enhanced_compliance_check(
                "I'm looking for a great moisturizer for dry skin."
            )
            
            assert result["status"] == "approved"
            assert len(result["violations"]) == 0
            assert result["agent_id"] == compliance_agent.agent_id
            assert result["analysis_method"] == "hybrid"
    
    @pytest.mark.asyncio
    async def test_compliance_flagged_message(self, compliance_agent):
        """Test that messages with questionable content are flagged."""
        result = await compliance_agent._perform_compliance_check(
            "Do you have any miracle products that cure aging overnight?"
        )
        
        assert result["status"] == "flagged"
        assert len(result["violations"]) > 0
        assert any("miracle" in str(violation) for violation in result["violations"])
    
    @pytest.mark.asyncio
    async def test_compliance_blocked_message(self, compliance_agent):
        """Test that dangerous content is blocked."""
        result = await compliance_agent._perform_compliance_check(
            "I want products with mercury for skin whitening."
        )
        
        assert result["status"] == "blocked"
        assert len(result["violations"]) > 0
        assert any("mercury" in str(violation) for violation in result["violations"])
    
    @pytest.mark.asyncio
    async def test_conversation_state_processing(self, compliance_agent):
        """Test processing conversation state."""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="Hello, I need help with skincare."
        )
        
        result_state = await compliance_agent.process_conversation(state)
        
        assert compliance_agent.agent_id in result_state.active_agents
        assert "status" in result_state.compliance_result
        assert result_state.compliance_result["status"] == "approved"


class TestSalesAgent:
    """增强LLM驱动销售智能体测试套件。"""
    
    @pytest.fixture
    def sales_agent(self):
        """创建测试用销售智能体。"""
        return SalesAgent("test_tenant")
    
    def test_conversation_stage_analysis(self, sales_agent):
        """测试对话阶段检测。"""
        # 测试问候检测
        state_greeting = ConversationState(
            tenant_id="test_tenant",
            customer_input="Hi there!",
            conversation_history=[]
        )
        stage = sales_agent._analyze_conversation_stage(state_greeting)
        assert stage == "greeting"
        
        # 测试产品查询检测
        state_inquiry = ConversationState(
            tenant_id="test_tenant", 
            customer_input="I'm looking for a foundation.",
            conversation_history=[{"msg": "previous"}]
        )
        stage = sales_agent._analyze_conversation_stage(state_inquiry)
        assert stage == "product_inquiry"
        
        # 测试需求评估检测
        state_needs = ConversationState(
            tenant_id="test_tenant",
            customer_input="I have very dry skin and need help.",
            conversation_history=[{"msg": "previous"}]
        )
        stage = sales_agent._analyze_conversation_stage(state_needs)
        assert stage == "need_assessment"
    
    def test_customer_needs_assessment(self, sales_agent):
        """测试客户需求识别。"""
        needs = sales_agent._assess_customer_needs(
            "I have dry, sensitive skin and need a moisturizer",
            {}
        )
        
        assert "dryness" in needs["skin_concerns"]
        assert "sensitivity" in needs["skin_concerns"]
        assert "moisturizer" in needs["product_types"]
        assert needs["urgency"] == "normal"
        
        # 测试紧急程度检测
        urgent_needs = sales_agent._assess_customer_needs(
            "I need foundation today for a special event!",
            {}
        )
        assert urgent_needs["urgency"] == "high"
        assert "foundation" in urgent_needs["product_types"]
    
    @pytest.mark.asyncio
    async def test_llm_powered_conversation_processing(self, sales_agent):
        """测试带增强意图分析的LLM驱动对话处理。"""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="Hi! I'm looking for a good foundation for my oily skin.",
            compliance_result={"status": "approved"},
            intent_analysis={
                "intent": "product_inquiry",
                "conversation_stage": "consultation",
                "customer_profile": {
                    "skin_concerns": ["oiliness"],
                    "product_interests": ["makeup", "foundation"],
                    "skin_type_indicators": ["oily"],
                    "urgency": "medium",
                    "experience_level": "intermediate"
                }
            }
        )
        
        with patch.object(sales_agent, '_generate_llm_response', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Based on your oily skin, I'd recommend our oil-control foundation..."
            
            result_state = await sales_agent.process_conversation(state)
            
            assert sales_agent.agent_id in result_state.active_agents
            assert result_state.sales_response is not None
            assert "oily skin" in result_state.sales_response or mock_llm.called


class TestLLMAgents:
    """LLM驱动智能体测试套件。"""
    
    @pytest.fixture
    def sentiment_agent(self):
        return SentimentAnalysisAgent("test_tenant")
    
    @pytest.fixture  
    def intent_agent(self):
        return IntentAnalysisAgent("test_tenant")
    
    @pytest.fixture
    def product_agent(self):
        return ProductExpertAgent("test_tenant")
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_agent(self, sentiment_agent):
        """测试LLM驱动的情感分析。"""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="I'm so frustrated! Nothing works for my acne!"
        )
        
        with patch.object(sentiment_agent.llm_client, 'chat_completion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"sentiment": "negative", "score": -0.7, "confidence": 0.9, "reasoning": "Customer expressing frustration"}'
            
            result_state = await sentiment_agent.process_conversation(state)
            
            assert sentiment_agent.agent_id in result_state.active_agents
            assert result_state.sentiment_analysis is not None
            assert result_state.sentiment_analysis.get("sentiment") == "negative"
    
    @pytest.mark.asyncio
    async def test_enhanced_intent_analysis_with_field_extraction(self, intent_agent):
        """测试带LLM字段提取的增强意图分析。"""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="My skin has been really oily lately and I keep getting breakouts. I need something affordable."
        )
        
        with patch.object(intent_agent.llm_client, 'chat_completion', new_callable=AsyncMock) as mock_llm:
            mock_response = '''{
                "intent": "skin_concern_consultation",
                "conversation_stage": "consultation", 
                "customer_profile": {
                    "skin_concerns": ["oiliness", "acne"],
                    "urgency": "medium",
                    "budget_signals": ["budget_conscious"],
                    "skin_type_indicators": ["oily"]
                },
                "confidence": 0.85
            }'''
            mock_llm.return_value = mock_response
            
            result_state = await intent_agent.process_conversation(state)
            
            assert intent_agent.agent_id in result_state.active_agents
            assert result_state.intent_analysis is not None
            profile = result_state.intent_analysis.get("customer_profile", {})
            assert "oiliness" in profile.get("skin_concerns", [])
            assert "budget_conscious" in profile.get("budget_signals", [])
    
    @pytest.mark.asyncio
    async def test_product_expert_agent(self, product_agent):
        """测试AI驱动的产品推荐。""" 
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="I need a cleanser for sensitive skin",
            customer_profile={"skin_type": "sensitive", "budget_preference": "medium"}
        )
        
        with patch.object(product_agent.llm_client, 'chat_completion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "For sensitive skin, I recommend our gentle cream cleanser..."
            
            result_state = await product_agent.process_conversation(state)
            
            assert product_agent.agent_id in result_state.active_agents
            assert product_agent.agent_id in result_state.agent_responses
            recommendations = result_state.agent_responses[product_agent.agent_id].get("product_recommendations")
            assert recommendations is not None


class TestCompleteAgentSystem:
    """完整的9智能体系统集成测试套件。"""
    
    def test_complete_9_agent_set_creation(self):
        """测试创建完整的9智能体LLM驱动系统。"""
        tenant_id = "complete_system_test"
        
        # 清除任何现有智能体
        agents_to_remove = [
            agent_id for agent_id in agent_registry.agents.keys()
            if agent_id.endswith(f"_{tenant_id}")
        ]
        for agent_id in agents_to_remove:
            del agent_registry.agents[agent_id]
        
        # 创建完整智能体集合
        agents = create_agent_set(tenant_id)
        
        # 验证所0个智能体都被创建
        expected_agents = {
            "compliance": ComplianceAgent,
            "sentiment": SentimentAnalysisAgent,
            "intent": IntentAnalysisAgent,
            "sales": SalesAgent,
            "product": ProductExpertAgent,
            "memory": MemoryAgent,
            "strategy": MarketStrategyCoordinator,
            "proactive": ProactiveAgent,
            "suggestion": AISuggestionAgent
        }
        
        assert len(agents) == 9, f"Expected 9 agents, got {len(agents)}"
        
        for agent_type, agent_class in expected_agents.items():
            assert agent_type in agents, f"Missing agent: {agent_type}"
            assert isinstance(agents[agent_type], agent_class), f"Wrong type for {agent_type}"
        
        # 验证智能体被正确注册
        registered_count = len([
            agent_id for agent_id in agent_registry.agents.keys()
            if agent_id.endswith(f"_{tenant_id}")
        ])
        assert registered_count == 9, f"Expected 9 registered agents, got {registered_count}"
    
    @pytest.mark.asyncio
    async def test_orchestrator_conversation_flow(self):
        """Test end-to-end conversation flow through orchestrator."""
        tenant_id = "orchestrator_test"
        
        # Ensure agents exist
        create_agent_set(tenant_id)
        
        # Get orchestrator
        orchestrator = get_orchestrator(tenant_id)
        
        # Process a conversation
        result = await orchestrator.process_conversation(
            customer_input="Hello! I'm looking for skincare help.",
            customer_id="test_customer"
        )
        
        assert result.conversation_id is not None
        assert result.tenant_id == tenant_id
        assert result.customer_input == "Hello! I'm looking for skincare help."
        assert result.processing_complete == True
        
        # Verify compliance was processed
        assert "status" in result.compliance_result
        
        # Verify agents were active
        expected_compliance_agent = f"compliance_review_{tenant_id}"
        assert expected_compliance_agent in result.active_agents
    
    def test_compliance_rule_creation(self):
        """Test creating custom compliance rules."""
        rule = ComplianceRule(
            rule_id="test_rule",
            pattern=r"\btest_pattern\b",
            severity="medium",
            message="Test rule triggered",
            action="flag"
        )
        
        # Test pattern matching
        violation = rule.check("This contains test_pattern in it")
        assert violation is not None
        assert violation["rule_id"] == "test_rule"
        assert violation["severity"] == "medium"
        
        # Test no match
        no_violation = rule.check("This doesn't contain the pattern")
        assert no_violation is None


class TestPerformanceMetrics:
    """Test suite for performance tracking and metrics."""
    
    def test_agent_statistics_tracking(self):
        """Test that agents track processing statistics."""
        agent = ComplianceAgent("metrics_test")
        
        initial_stats = agent.processing_stats.copy()
        assert initial_stats["messages_processed"] == 0
        assert initial_stats["errors"] == 0
        
        # Simulate processing
        agent.update_stats()
        
        updated_stats = agent.processing_stats
        assert updated_stats["messages_processed"] == 1
        assert updated_stats["last_activity"] is not None
    
    def test_sales_agent_metrics(self):
        """Test sales agent specific metrics."""
        agent = SalesAgent("metrics_test")
        
        metrics = agent.get_conversation_metrics()
        
        assert "total_conversations" in metrics
        assert "error_rate" in metrics
        assert "agent_id" in metrics
        assert "tenant_id" in metrics
        assert metrics["tenant_id"] == "metrics_test"


# Integration test for API-level functionality
class TestAPIIntegration:
    """Test API integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_mock_conversation_flow(self):
        """Test a complete conversation flow with mocked external dependencies."""
        tenant_id = "api_test"
        
        # Create agents
        create_agent_set(tenant_id)
        
        # Get orchestrator
        orchestrator = get_orchestrator(tenant_id)
        
        # Test various conversation scenarios
        test_scenarios = [
            {
                "input": "Hi! I need help with makeup.",
                "expected_compliance": "approved",
                "expected_processing": True
            },
            {
                "input": "Do you have miracle anti-aging products?",
                "expected_compliance": "flagged", 
                "expected_processing": True
            },
            {
                "input": "I want products with dangerous mercury ingredients.",
                "expected_compliance": "blocked",
                "expected_processing": True  # Processing completes but with error state
            }
        ]
        
        for scenario in test_scenarios:
            result = await orchestrator.process_conversation(
                customer_input=scenario["input"],
                customer_id="api_test_customer"
            )
            
            assert result.processing_complete == scenario["expected_processing"]
            assert result.compliance_result["status"] == scenario["expected_compliance"]
            
            if scenario["expected_compliance"] == "blocked":
                assert result.error_state == "compliance_violation"
                assert result.final_response != ""  # Should have user-facing message


if __name__ == "__main__":
    # Run basic tests manually
    async def run_basic_tests():
        print("Running basic agent system tests...")
        
        # Test compliance agent
        compliance = ComplianceAgent("manual_test")
        result = await compliance._perform_compliance_check("Hello, I need skincare help.")
        print(f"Compliance test result: {result['status']}")
        
        # Test sales agent  
        sales = SalesAgent("manual_test")
        state = ConversationState(
            tenant_id="manual_test",
            customer_input="Hi there!",
            compliance_result={"status": "approved"},
            intent_analysis={"market_strategy": "premium"}
        )
        result_state = await sales.process_conversation(state)
        print(f"Sales agent processed: {sales.agent_id in result_state.active_agents}")
        
        # Test orchestrator
        create_agent_set("manual_test")
        orchestrator = get_orchestrator("manual_test")
        result = await orchestrator.process_conversation(
            customer_input="Hello! I'm looking for foundation recommendations.",
            customer_id="test_customer"
        )
        print(f"Orchestrator result: Processing complete = {result.processing_complete}")
        print(f"Compliance status: {result.compliance_result.get('status', 'unknown')}")
        
        print("Basic tests completed successfully!")
    
    asyncio.run(run_basic_tests()) 