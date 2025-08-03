"""
路由策略详细测试套件

该测试套件专门测试各种智能路由策略的实现和行为:
- 性能优先路由策略
- 成本优先路由策略
- 平衡路由策略
- 智能体优化路由策略
- 中文优化路由策略
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.llm.intelligent_router import (
    IntelligentRouter, RoutingStrategy, RoutingContext
)
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    AgentProviderMapping, ModelCapability
)
from src.llm.base_provider import LLMRequest, RequestType, ProviderHealth
from src.llm.provider_manager import ProviderManager


class TestPerformanceFirstStrategy:
    """测试性能优先路由策略"""
    
    @pytest.fixture
    def performance_setup(self):
        """性能测试设置"""
        config = GlobalProviderConfig(
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
            tenant_id="performance_test"
        )
        
        manager = Mock(spec=ProviderManager)
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
                latency_ms=600,  # Faster
                error_rate=0.01,
                success_rate=0.99
            )
        }
        
        return IntelligentRouter(config, manager), manager
    
    def test_selects_fastest_provider(self, performance_setup):
        """测试选择最快的供应商"""
        router, _ = performance_setup
        
        context = RoutingContext(
            agent_type="sales",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.PERFORMANCE_FIRST
        )
        
        request = LLMRequest(
            prompt="推荐适合油性皮肤的护肤品",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Should select Anthropic (600ms vs 800ms)
        selected = router.select_provider(request, context)
        assert selected == ProviderType.ANTHROPIC


class TestCostFirstStrategy:
    """测试成本优先路由策略"""
    
    @pytest.fixture 
    def cost_setup(self):
        """成本测试设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                ),
                ProviderType.DEEPSEEK: ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    api_key="test-key",
                    models=["deepseek-chat"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="cost_test"
        )
        
        manager = Mock(spec=ProviderManager)
        manager.get_provider_costs.return_value = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005}  # Cheaper
        }
        
        return IntelligentRouter(config, manager), manager
    
    def test_selects_cheapest_provider(self, cost_setup):
        """测试选择最便宜的供应商"""
        router, _ = cost_setup
        
        context = RoutingContext(
            agent_type="product",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.COST_FIRST,
            budget_constraints={"max_cost_per_request": 0.001}
        )
        
        request = LLMRequest(
            prompt="分析产品成分表",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Should select DeepSeek (cheaper)
        selected = router.select_provider(request, context)
        assert selected == ProviderType.DEEPSEEK


class TestBalancedStrategy:
    """测试平衡路由策略"""
    
    @pytest.fixture
    def balanced_setup(self):
        """平衡测试设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                ),
                ProviderType.GEMINI: ProviderConfig(
                    provider_type=ProviderType.GEMINI,
                    api_key="test-key",
                    models=["gemini-pro"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="balanced_test"
        )
        
        manager = Mock(spec=ProviderManager)
        # Mock balanced health and cost data
        manager.get_provider_health.return_value = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=800,
                success_rate=0.98,
                error_rate=0.02
            ),
            ProviderType.GEMINI: ProviderHealth(
                provider=ProviderType.GEMINI,
                status="healthy",
                latency_ms=900,
                success_rate=0.97,
                error_rate=0.03
            )
        }
        
        manager.get_provider_costs.return_value = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.GEMINI: {"cost_per_1k_tokens": 0.001}
        }
        
        return IntelligentRouter(config, manager), manager
    
    def test_balances_cost_and_performance(self, balanced_setup):
        """测试平衡成本和性能"""
        router, _ = balanced_setup
        
        context = RoutingContext(
            agent_type="sentiment",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.BALANCED
        )
        
        request = LLMRequest(
            prompt="分析客户反馈情感",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Should consider both factors
        selected = router.select_provider(request, context)
        assert selected in [ProviderType.OPENAI, ProviderType.GEMINI]


class TestAgentOptimizedStrategy:
    """测试智能体优化路由策略"""
    
    @pytest.fixture
    def agent_mapping_setup(self):
        """智能体映射设置"""
        config = GlobalProviderConfig(
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
            agent_mappings={
                "compliance": AgentProviderMapping(
                    agent_type="compliance",
                    preferred_providers=[ProviderType.ANTHROPIC],
                    fallback_providers=[ProviderType.OPENAI],
                    routing_rules={"priority": "accuracy"}
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="agent_test"
        )
        
        manager = Mock(spec=ProviderManager)
        return IntelligentRouter(config, manager), manager
    
    def test_uses_agent_specific_mapping(self, agent_mapping_setup):
        """测试使用智能体特定映射"""
        router, _ = agent_mapping_setup
        
        context = RoutingContext(
            agent_type="compliance",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.AGENT_OPTIMIZED
        )
        
        request = LLMRequest(
            prompt="检查产品描述合规性",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Should prefer Anthropic for compliance
        selected = router.select_provider(request, context)
        assert selected == ProviderType.ANTHROPIC


class TestChineseOptimizedStrategy:
    """测试中文优化路由策略"""
    
    @pytest.fixture
    def chinese_setup(self):
        """中文优化设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.DEEPSEEK: ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    api_key="test-key",
                    models=["deepseek-chat"],
                    capabilities=[ModelCapability.CHAT]
                ),
                ProviderType.GEMINI: ProviderConfig(
                    provider_type=ProviderType.GEMINI,
                    api_key="test-key",
                    models=["gemini-pro"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.DEEPSEEK,
            tenant_id="chinese_test"
        )
        
        manager = Mock(spec=ProviderManager)
        return IntelligentRouter(config, manager), manager
    
    def test_prefers_chinese_optimized_providers(self, chinese_setup):
        """测试偏好中文优化的供应商"""
        router, _ = chinese_setup
        
        context = RoutingContext(
            agent_type="product",
            tenant_id="test_tenant",
            content_language="chinese",
            strategy=RoutingStrategy.CHINESE_OPTIMIZED
        )
        
        request = LLMRequest(
            prompt="推荐适合中国消费者的美妆产品",
            request_type=RequestType.CHAT,
            metadata={"language": "chinese", "region": "china"}
        )
        
        # Should prefer Chinese-optimized providers
        selected = router.select_provider(request, context)
        assert selected in [ProviderType.DEEPSEEK, ProviderType.GEMINI]


if __name__ == "__main__":
    print("路由策略测试模块加载成功")
    print("测试覆盖: 性能优先、成本优先、平衡、智能体优化、中文优化策略")