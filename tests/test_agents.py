"""
Agent System Tests

Basic tests to verify the multi-agent system functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.agents.core import ConversationState, AgentMessage
from src.agents.compliance import ComplianceAgent, ComplianceRule
from src.agents.sales import SalesAgent
from src.agents import create_agent_set, get_orchestrator, agent_registry


class TestComplianceAgent:
    """Test suite for Compliance Agent."""
    
    @pytest.fixture
    def compliance_agent(self):
        """Create a test compliance agent."""
        return ComplianceAgent("test_tenant")
    
    @pytest.mark.asyncio
    async def test_compliance_approved_message(self, compliance_agent):
        """Test that clean messages are approved."""
        result = await compliance_agent._perform_compliance_check(
            "I'm looking for a great moisturizer for dry skin."
        )
        
        assert result["status"] == "approved"
        assert len(result["violations"]) == 0
        assert result["agent_id"] == compliance_agent.agent_id
    
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
    """Test suite for Sales Agent."""
    
    @pytest.fixture
    def sales_agent(self):
        """Create a test sales agent."""
        return SalesAgent("test_tenant")
    
    def test_conversation_stage_analysis(self, sales_agent):
        """Test conversation stage detection."""
        # Test greeting detection
        state_greeting = ConversationState(
            tenant_id="test_tenant",
            customer_input="Hi there!",
            conversation_history=[]
        )
        stage = sales_agent._analyze_conversation_stage(state_greeting)
        assert stage == "greeting"
        
        # Test product inquiry detection
        state_inquiry = ConversationState(
            tenant_id="test_tenant", 
            customer_input="I'm looking for a foundation.",
            conversation_history=[{"msg": "previous"}]
        )
        stage = sales_agent._analyze_conversation_stage(state_inquiry)
        assert stage == "product_inquiry"
        
        # Test need assessment detection
        state_needs = ConversationState(
            tenant_id="test_tenant",
            customer_input="I have very dry skin and need help.",
            conversation_history=[{"msg": "previous"}]
        )
        stage = sales_agent._analyze_conversation_stage(state_needs)
        assert stage == "need_assessment"
    
    def test_customer_needs_assessment(self, sales_agent):
        """Test customer needs identification."""
        needs = sales_agent._assess_customer_needs(
            "I have dry, sensitive skin and need a moisturizer",
            {}
        )
        
        assert "dryness" in needs["skin_concerns"]
        assert "sensitivity" in needs["skin_concerns"]
        assert "moisturizer" in needs["product_types"]
        assert needs["urgency"] == "normal"
        
        # Test urgency detection
        urgent_needs = sales_agent._assess_customer_needs(
            "I need foundation today for a special event!",
            {}
        )
        assert urgent_needs["urgency"] == "high"
        assert "foundation" in urgent_needs["product_types"]
    
    @pytest.mark.asyncio
    async def test_conversation_processing(self, sales_agent):
        """Test full conversation processing."""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="Hi! I'm looking for a good foundation.",
            compliance_result={"status": "approved"},
            intent_analysis={"market_strategy": "premium"}
        )
        
        result_state = await sales_agent.process_conversation(state)
        
        assert sales_agent.agent_id in result_state.active_agents
        assert sales_agent.agent_id in result_state.agent_responses
        
        response_data = result_state.agent_responses[sales_agent.agent_id]
        assert "response" in response_data
        assert "strategy_used" in response_data
        assert "conversation_stage" in response_data


class TestAgentIntegration:
    """Test suite for agent integration and orchestration."""
    
    def test_agent_set_creation(self):
        """Test creating a complete agent set."""
        tenant_id = "integration_test"
        
        # Clear any existing agents
        agents_to_remove = [
            agent_id for agent_id in agent_registry.agents.keys()
            if agent_id.endswith(f"_{tenant_id}")
        ]
        for agent_id in agents_to_remove:
            del agent_registry.agents[agent_id]
        
        # Create new agent set
        agents = create_agent_set(tenant_id)
        
        assert "compliance" in agents
        assert "sales" in agents
        assert isinstance(agents["compliance"], ComplianceAgent)
        assert isinstance(agents["sales"], SalesAgent)
        
        # Verify agents are registered
        compliance_id = f"compliance_review_{tenant_id}"
        sales_id = f"sales_agent_{tenant_id}"
        
        assert agent_registry.get_agent(compliance_id) is not None
        assert agent_registry.get_agent(sales_id) is not None
    
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