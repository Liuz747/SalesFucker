"""
智能路由系统核心测试套件

该测试套件专注于智能路由系统的核心功能测试:
- 路由策略基础测试
- 智能路由器初始化测试
- 基本路由决策验证

更多专业测试请参见:
- test_routing_strategies.py (路由策略详细测试)
- test_routing_engines.py (评分和规则引擎测试)
- test_routing_learning.py (学习引擎测试)
- test_routing_scenarios.py (集成场景测试)
"""

import pytest

@pytest.mark.skip(reason="Feature removed in simplified LLM system")
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from datetime import datetime

# Note: Intelligent routing simplified in new system
    IntelligentRouter, RoutingStrategy, RoutingContext,
    ProviderScore, RoutingDecision
)
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType
    ProviderType, GlobalProviderConfig, ProviderConfig,
    ModelCapability
)
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.providers.base import BaseProvider
# Note: Provider management simplified in new system


class TestIntelligentRouterCore:
    """测试智能路由器核心功能"""
    
    @pytest.fixture
    def mock_provider_manager(self):
        """模拟供应商管理器"""
        manager = Mock(spec=ProviderManager)
        
        # Mock basic health data
        manager.get_provider_health.return_value = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                last_check=datetime.now(),
                latency_ms=800,
                error_rate=0.02,
                success_rate=0.98
            ),
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="healthy", 
                last_check=datetime.now(),
                latency_ms=600,
                error_rate=0.01,
                success_rate=0.99
            )
        }
        
        # Mock cost data
        manager.get_provider_costs.return_value = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.ANTHROPIC: {"cost_per_1k_tokens": 0.003}
        }
        
        return manager
    
    @pytest.fixture
    def basic_config(self):
        """基础配置fixture"""
        return GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-sonnet"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="routing_test"
        )
    
    def test_router_initialization(self, mock_provider_manager, basic_config):
        """测试路由器初始化"""
        router = IntelligentRouter(basic_config, mock_provider_manager)
        
        assert router.config == basic_config
        assert router.provider_manager == mock_provider_manager
        assert router.scoring_engine is not None
        assert router.rule_engine is not None
        assert router.selection_engine is not None
    
    def test_basic_provider_selection(self, mock_provider_manager, basic_config):
        """测试基础供应商选择"""
        router = IntelligentRouter(basic_config, mock_provider_manager)
        
        context = RoutingContext(
            agent_type="sales",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.PERFORMANCE_FIRST
        )
        
        request = LLMRequest(
            prompt="测试请求",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Should select a valid provider
        selected_provider = router.select_provider(request, context)
        assert selected_provider in [ProviderType.OPENAI, ProviderType.ANTHROPIC]
    
    def test_routing_context_creation(self):
        """测试路由上下文创建"""
        context = RoutingContext(
            agent_type="product",
            tenant_id="test_tenant",
            conversation_id="conv_123",
            strategy=RoutingStrategy.BALANCED
        )
        
        assert context.agent_type == "product"
        assert context.tenant_id == "test_tenant"
        assert context.conversation_id == "conv_123"
        assert context.strategy == RoutingStrategy.BALANCED


class TestBasicRoutingFlow:
    """测试基础路由流程"""
    
    @pytest.mark.asyncio
    async def test_routing_decision_creation(self):
        """测试路由决策创建"""
        decision = RoutingDecision(
            selected_provider=ProviderType.OPENAI,
            decision_reason="test_reason",
            provider_score=ProviderScore(
                provider=ProviderType.OPENAI,
                total_score=0.85,
                performance_score=0.8,
                cost_score=0.9,
                reliability_score=0.85
            ),
            applied_rules=["rule_1"],
            fallback_used=False
        )
        
        assert decision.selected_provider == ProviderType.OPENAI
        assert decision.decision_reason == "test_reason"
        assert decision.provider_score.total_score == 0.85
        assert "rule_1" in decision.applied_rules
        assert not decision.fallback_used
    
    def test_provider_score_calculation(self):
        """测试供应商评分计算"""
        score = ProviderScore(
            provider=ProviderType.ANTHROPIC,
            total_score=0.92,
            performance_score=0.95,
            cost_score=0.85,
            reliability_score=0.98
        )
        
        assert score.provider == ProviderType.ANTHROPIC
        assert score.total_score == 0.92
        assert score.performance_score == 0.95
        assert score.cost_score == 0.85
        assert score.reliability_score == 0.98


if __name__ == "__main__":
    # 运行基础路由测试
    async def run_basic_routing_tests():
        print("运行基础智能路由测试...")
        
        # 测试路由上下文
        context = RoutingContext(
            agent_type="sales",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.BALANCED
        )
        print(f"路由上下文创建成功: {context.agent_type}")
        
        # 测试请求对象
        request = LLMRequest(
            prompt="测试路由请求",
            request_type=RequestType.CHAT,
            model="auto"
        )
        print(f"路由请求创建成功: {request.request_type}")
        
        # 测试评分引擎
        scoring_engine = ScoringEngine()
        criteria = ScoringCriteria(
            performance_weight=0.5,
            cost_weight=0.3,
            reliability_weight=0.2
        )
        print(f"评分引擎初始化成功: {criteria.performance_weight}")
        
        print("基础智能路由测试完成!")
    
    asyncio.run(run_basic_routing_tests())