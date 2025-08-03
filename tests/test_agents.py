"""
增强的LLM驱动多智能体系统测试

完整的9智能体LLM驱动系统的综合测试。
测试包括所有智能体、多LLM集成、智能路由和端到端工作流。

更新内容:
- 集成多LLM供应商支持
- 测试智能体特定供应商路由
- 测试故障转移和成本优化
- 测试中文内容优化路由
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

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

# Multi-LLM system imports
from src.llm.multi_llm_client import MultiLLMClient, get_multi_llm_client
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    AgentProviderMapping, ModelCapability, ProviderCredentials
)
from src.llm.base_provider import LLMRequest, LLMResponse, RequestType, ProviderError
from src.llm.intelligent_router import RoutingStrategy, RoutingContext
from src.llm.cost_optimizer import CostOptimizer
from src.llm.failover_system import FailoverSystem


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
    
    @pytest.mark.asyncio
    async def test_compliance_multi_llm_provider_routing(self, compliance_agent):
        """测试合规智能体的多LLM供应商路由。"""
        # Mock multi-LLM client
        mock_multi_llm = Mock(spec=MultiLLMClient)
        mock_response = LLMResponse(
            request_id="test_req_001",
            provider_type=ProviderType.ANTHROPIC,
            model="claude-3-sonnet",
            content='{"compliant": true, "violations": [], "confidence": 0.95, "reasoning": "Content is appropriate for cosmetics marketing"}',
            usage_tokens=80,
            cost=0.002,
            response_time=0.6
        )
        mock_multi_llm.chat_completion = AsyncMock(return_value=mock_response)
        
        with patch.object(compliance_agent, 'llm_client', mock_multi_llm):
            result = await compliance_agent._llm_compliance_analysis(
                "推荐适合敏感肌肤的温和洁面产品",
                routing_context={"strategy": RoutingStrategy.AGENT_OPTIMIZED}
            )
            
            # Verify request was routed to appropriate provider for compliance
            mock_multi_llm.chat_completion.assert_called_once()
            call_args = mock_multi_llm.chat_completion.call_args
            messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0]
            
            # Verify compliance-specific routing
            assert mock_multi_llm.chat_completion.called
            assert "agent_type" in call_args[1] and call_args[1]["agent_type"] == "compliance"
    
    @pytest.mark.asyncio
    async def test_compliance_failover_scenario(self, compliance_agent):
        """测试合规智能体故障转移场景。"""
        mock_multi_llm = Mock(spec=MultiLLMClient)
        
        # First call fails, second succeeds (failover)
        primary_error = ProviderError("Primary provider rate limited", ProviderType.ANTHROPIC, "RATE_LIMIT")
        fallback_response = LLMResponse(
            request_id="test_req_002",
            provider_type=ProviderType.OPENAI,
            model="gpt-4",
            content='{"compliant": true, "violations": [], "confidence": 0.92, "reasoning": "Fallback analysis successful"}',
            usage_tokens=85,
            cost=0.003,
            response_time=0.8
        )
        
        mock_multi_llm.chat_completion = AsyncMock(side_effect=[primary_error, fallback_response])
        
        with patch.object(compliance_agent, 'llm_client', mock_multi_llm):
            # Should handle failover gracefully
            result = await compliance_agent._llm_compliance_analysis(
                "测试故障转移场景",
                max_retries=1
            )
            
            # Should eventually succeed with fallback
            assert result is not None
            assert mock_multi_llm.chat_completion.call_count == 2


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
    async def test_sentiment_analysis_agent_with_multi_llm(self, sentiment_agent):
        """测试使用多LLM的情感分析智能体。"""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="I'm so frustrated! Nothing works for my acne!"
        )
        
        # Mock multi-LLM response with Chinese optimization
        mock_response = LLMResponse(
            request_id="sentiment_req_001",
            provider_type=ProviderType.GEMINI,  # Optimized for sentiment analysis
            model="gemini-pro",
            content='{"sentiment": "negative", "score": -0.7, "confidence": 0.9, "reasoning": "Customer expressing frustration", "language": "english"}',
            usage_tokens=65,
            cost=0.001,
            response_time=0.4
        )
        
        with patch.object(sentiment_agent, 'llm_client') as mock_multi_llm:
            mock_multi_llm.analyze_sentiment = AsyncMock(return_value={
                "sentiment": "negative", "score": -0.7, "confidence": 0.9
            })
            
            result_state = await sentiment_agent.process_conversation(state)
            
            assert sentiment_agent.agent_id in result_state.active_agents
            assert result_state.sentiment_analysis is not None
            assert result_state.sentiment_analysis.get("sentiment") == "negative"
            
            # Verify multi-LLM client was called with sentiment-specific routing
            mock_multi_llm.analyze_sentiment.assert_called_once()
            call_args = mock_multi_llm.analyze_sentiment.call_args
            assert call_args[0][0] == "I'm so frustrated! Nothing works for my acne!"
    
    @pytest.mark.asyncio
    async def test_enhanced_intent_analysis_with_multi_llm(self, intent_agent):
        """测试使用多LLM的增强意图分析。"""
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="My skin has been really oily lately and I keep getting breakouts. I need something affordable."
        )
        
        # Mock multi-LLM client for intent analysis
        mock_intent_result = {
            "intent": "skin_concern_consultation",
            "conversation_stage": "consultation", 
            "customer_profile": {
                "skin_concerns": ["oiliness", "acne"],
                "urgency": "medium",
                "budget_signals": ["budget_conscious"],
                "skin_type_indicators": ["oily"]
            },
            "confidence": 0.85
        }
        
        with patch.object(intent_agent, 'llm_client') as mock_multi_llm:
            mock_multi_llm.classify_intent = AsyncMock(return_value=mock_intent_result)
            
            result_state = await intent_agent.process_conversation(state)
            
            assert intent_agent.agent_id in result_state.active_agents
            assert result_state.intent_analysis is not None
            profile = result_state.intent_analysis.get("customer_profile", {})
            assert "oiliness" in profile.get("skin_concerns", [])
            assert "budget_conscious" in profile.get("budget_signals", [])
            
            # Verify intent-specific routing and conversation history handling
            mock_multi_llm.classify_intent.assert_called_once()
            call_args = mock_multi_llm.classify_intent.call_args
            assert call_args[1]["tenant_id"] == "test_tenant"
    
    @pytest.mark.asyncio
    async def test_product_expert_agent_with_multi_llm(self, product_agent):
        """测试使用多LLM的产品专家智能体。""" 
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="I need a cleanser for sensitive skin",
            customer_profile={"skin_type": "sensitive", "budget_preference": "medium"}
        )
        
        # Mock product recommendations with RAG-enhanced responses
        mock_product_response = {
            "recommendations": [
                {
                    "product_name": "Gentle Foam Cleanser",
                    "price": "$25",
                    "suitability_score": 0.95,
                    "reason": "Specifically formulated for sensitive skin"
                }
            ],
            "reasoning": "For sensitive skin, I recommend our gentle cream cleanser...",
            "confidence": 0.9
        }
        
        with patch.object(product_agent, 'llm_client') as mock_multi_llm:
            mock_multi_llm.chat_completion = AsyncMock(return_value=mock_product_response)
            
            result_state = await product_agent.process_conversation(state)
            
            assert product_agent.agent_id in result_state.active_agents
            assert product_agent.agent_id in result_state.agent_responses
            
            # Verify product-specific routing with RAG integration
            mock_multi_llm.chat_completion.assert_called_once()
            call_args = mock_multi_llm.chat_completion.call_args
            assert call_args[1]["agent_type"] == "product"


class TestMultiLLMAgentIntegration:
    """测试多LLM智能体集成功能。"""
    
    @pytest.fixture
    def multi_llm_config(self):
        """多LLM配置fixture。"""
        return GlobalProviderConfig(
            default_providers={
                "openai": ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.OPENAI,
                        api_key="test-openai-key"
                    ),
                    is_enabled=True,
                    priority=1
                ),
                "anthropic": ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.ANTHROPIC,
                        api_key="test-anthropic-key"
                    ),
                    is_enabled=True,
                    priority=2
                ),
                "gemini": ProviderConfig(
                    provider_type=ProviderType.GEMINI,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.GEMINI,
                        api_key="test-gemini-key"
                    ),
                    is_enabled=True,
                    priority=3
                )
            }
        )
    
    @pytest.mark.asyncio
    async def test_agent_provider_optimization_routing(self, multi_llm_config):
        """测试智能体特定的供应商优化路由。"""
        # Create multi-LLM client
        with patch('src.llm.multi_llm_client.MultiLLMClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.chat_completion = AsyncMock(return_value=LLMResponse(
                request_id="test_req",
                provider_type=ProviderType.ANTHROPIC,
                model="claude-3-sonnet",
                content="Compliance analysis complete",
                usage_tokens=100,
                cost=0.003,
                response_time=0.7
            ))
            
            # Test compliance agent routing (should prefer Anthropic)
            compliance_agent = ComplianceAgent("test_tenant")
            compliance_agent.llm_client = mock_client
            
            result = await compliance_agent._llm_compliance_analysis(
                "检查化妆品广告内容合规性",
                routing_context={"strategy": RoutingStrategy.AGENT_OPTIMIZED}
            )
            
            # Verify appropriate provider selection
            mock_client.chat_completion.assert_called_once()
            call_kwargs = mock_client.chat_completion.call_args[1]
            assert call_kwargs["agent_type"] == "compliance"
            assert call_kwargs["strategy"] == RoutingStrategy.AGENT_OPTIMIZED
    
    @pytest.mark.asyncio
    async def test_chinese_language_optimization_routing(self, multi_llm_config):
        """测试中文语言优化路由。"""
        with patch('src.llm.multi_llm_client.MultiLLMClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.analyze_sentiment = AsyncMock(return_value={
                "sentiment": "positive",
                "score": 0.8,
                "confidence": 0.9,
                "cultural_context": "Chinese customer satisfaction"
            })
            
            # Test sentiment analysis with Chinese content
            sentiment_agent = SentimentAnalysisAgent("test_tenant")
            sentiment_agent.llm_client = mock_client
            
            state = ConversationState(
                tenant_id="test_tenant",
                customer_input="这个面霜真的很好用，我的皮肤变得很光滑！",
                metadata={"language": "chinese"}
            )
            
            result_state = await sentiment_agent.process_conversation(state)
            
            # Verify Chinese optimization was applied
            mock_client.analyze_sentiment.assert_called_once()
            call_args = mock_client.analyze_sentiment.call_args
            assert "中文" in call_args[0][0] or "chinese" in str(call_args[1]).lower()


class TestCompleteAgentSystem:
    """完整的9智能体系统集成测试套件。"""
    
    def test_complete_9_agent_set_with_multi_llm(self):
        """测试创建完整的9智能体多LLM系统。"""
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
        
        # 验证所有9个智能体都被创建
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
            
            # Verify each agent has multi-LLM capabilities
            agent = agents[agent_type]
            assert hasattr(agent, 'llm_client'), f"Agent {agent_type} missing llm_client"
        
        # 验证智能体被正确注册
        registered_count = len([
            agent_id for agent_id in agent_registry.agents.keys()
            if agent_id.endswith(f"_{tenant_id}")
        ])
        assert registered_count == 9, f"Expected 9 registered agents, got {registered_count}"
    
    @pytest.mark.asyncio
    async def test_orchestrator_multi_llm_conversation_flow(self):
        """测试通过编排器的端到端多LLM对话流程。"""
        tenant_id = "orchestrator_test"
        
        # Mock multi-LLM client for all agents
        with patch('src.llm.multi_llm_client.get_multi_llm_client') as mock_get_client:
            mock_client = Mock(spec=MultiLLMClient)
            mock_get_client.return_value = mock_client
            
            # Setup mock responses for different agent types
            mock_client.chat_completion = AsyncMock(return_value=LLMResponse(
                request_id="orch_test_001",
                provider_type=ProviderType.OPENAI,
                model="gpt-4",
                content="Response from multi-LLM system",
                usage_tokens=120,
                cost=0.004,
                response_time=0.9
            ))
            
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
            
            # Verify agents were active with multi-LLM support
            expected_compliance_agent = f"compliance_review_{tenant_id}"
            assert expected_compliance_agent in result.active_agents
            
            # Verify multi-LLM client was used
            assert mock_client.chat_completion.called
    
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
class TestMultiLLMAPIIntegration:
    """测试多LLM API集成场景。"""
    
    @pytest.mark.asyncio
    async def test_multi_provider_conversation_flow(self):
        """测试多供应商对话流程。"""
        tenant_id = "api_test"
        
        # Mock different providers for different scenarios
        with patch('src.llm.multi_llm_client.get_multi_llm_client') as mock_get_client:
            mock_client = Mock(spec=MultiLLMClient)
            mock_get_client.return_value = mock_client
            
            # Setup different provider responses for different scenarios
            def mock_chat_completion(*args, **kwargs):
                agent_type = kwargs.get('agent_type', 'unknown')
                if agent_type == 'compliance':
                    return LLMResponse(
                        request_id="comp_001",
                        provider_type=ProviderType.ANTHROPIC,
                        model="claude-3-sonnet",
                        content='{"status": "approved", "violations": []}',
                        usage_tokens=50,
                        cost=0.002,
                        response_time=0.6
                    )
                elif agent_type == 'sentiment':
                    return LLMResponse(
                        request_id="sent_001",
                        provider_type=ProviderType.GEMINI,
                        model="gemini-pro",
                        content='{"sentiment": "positive", "score": 0.8}',
                        usage_tokens=40,
                        cost=0.001,
                        response_time=0.4
                    )
                else:
                    return LLMResponse(
                        request_id="default_001",
                        provider_type=ProviderType.OPENAI,
                        model="gpt-4",
                        content="General response",
                        usage_tokens=60,
                        cost=0.003,
                        response_time=0.8
                    )
            
            mock_client.chat_completion = AsyncMock(side_effect=mock_chat_completion)
            mock_client.analyze_sentiment = AsyncMock(return_value={"sentiment": "positive", "score": 0.8})
            mock_client.classify_intent = AsyncMock(return_value={"intent": "product_inquiry"})
            
            # Create agents
            create_agent_set(tenant_id)
            
            # Get orchestrator
            orchestrator = get_orchestrator(tenant_id)
            
            # Test conversation with multi-provider routing
            result = await orchestrator.process_conversation(
                customer_input="Hi! I need help with makeup.",
                customer_id="api_test_customer"
            )
            
            assert result.processing_complete == True
            assert result.compliance_result["status"] == "approved"
            
            # Verify multiple providers were used
            assert mock_client.chat_completion.call_count >= 1


if __name__ == "__main__":
    # Run basic multi-LLM tests manually
    async def run_multi_llm_tests():
        print("Running multi-LLM agent system tests...")
        
        # Mock multi-LLM client for manual testing
        with patch('src.llm.multi_llm_client.get_multi_llm_client') as mock_get_client:
            mock_client = Mock(spec=MultiLLMClient)
            mock_get_client.return_value = mock_client
            
            mock_client.chat_completion = AsyncMock(return_value=LLMResponse(
                request_id="manual_test_001",
                provider_type=ProviderType.OPENAI,
                model="gpt-4",
                content="Test response from multi-LLM",
                usage_tokens=100,
                cost=0.005,
                response_time=1.0
            ))
            
            # Test compliance agent with multi-LLM
            compliance = ComplianceAgent("manual_test")
            compliance.llm_client = mock_client
            result = await compliance._perform_compliance_check("Hello, I need skincare help.")
            print(f"Multi-LLM compliance test result: {result['status']}")
            
            # Test sales agent with multi-LLM
            sales = SalesAgent("manual_test")
            sales.llm_client = mock_client
            state = ConversationState(
                tenant_id="manual_test",
                customer_input="Hi there!",
                compliance_result={"status": "approved"},
                intent_analysis={"market_strategy": "premium"}
            )
            result_state = await sales.process_conversation(state)
            print(f"Multi-LLM sales agent processed: {sales.agent_id in result_state.active_agents}")
            
            # Test orchestrator with multi-LLM
            create_agent_set("manual_test")
            orchestrator = get_orchestrator("manual_test")
            result = await orchestrator.process_conversation(
                customer_input="Hello! I'm looking for foundation recommendations.",
                customer_id="test_customer"
            )
            print(f"Multi-LLM orchestrator result: Processing complete = {result.processing_complete}")
            print(f"Compliance status: {result.compliance_result.get('status', 'unknown')}")
            
            print("Multi-LLM basic tests completed successfully!")
    
    asyncio.run(run_multi_llm_tests()) 