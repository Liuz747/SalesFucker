"""
路由集成场景测试套件

该测试套件专门测试真实世界的路由场景:
- 真实世界路由场景模拟
- 紧急情况路由处理
- 多供应商故障转移
- 复杂上下文路由决策
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.llm.intelligent_router import (
    IntelligentRouter, RoutingStrategy, RoutingContext
)
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig
)
from src.llm.base_provider import LLMRequest, RequestType, ProviderHealth
from src.llm.provider_manager import ProviderManager


class TestRealWorldRoutingScenarios:
    """测试真实世界路由场景"""
    
    @pytest.fixture
    def comprehensive_router_setup(self):
        """综合路由器设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4", "gpt-3.5-turbo"]
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-opus"]
                ),
                ProviderType.GEMINI: ProviderConfig(
                    provider_type=ProviderType.GEMINI,
                    api_key="test-key",
                    models=["gemini-pro"]
                ),
                ProviderType.DEEPSEEK: ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    api_key="test-key",
                    models=["deepseek-chat"]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="scenario_test"
        )
        
        provider_manager = Mock(spec=ProviderManager)
        router = IntelligentRouter(config, provider_manager)
        
        return router, provider_manager
    
    @pytest.mark.asyncio
    async def test_chinese_customer_scenario(self, comprehensive_router_setup):
        """测试中国客户产品推荐场景"""
        router, provider_manager = comprehensive_router_setup
        
        # Scenario: Chinese customer asking for product recommendations
        context = RoutingContext(
            agent_type="product",
            tenant_id="cosmetics_brand_cn",
            conversation_id="conv_456",
            content_language="chinese",
            strategy=RoutingStrategy.CHINESE_OPTIMIZED,
            customer_profile={
                "language": "chinese",
                "region": "china",
                "budget": "medium",
                "skin_type": "oily"
            }
        )
        
        request = LLMRequest(
            prompt="我想要一套适合油性皮肤的护肤品，预算在500-1000元",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={
                "language": "chinese",
                "intent": "product_recommendation",
                "urgency": "normal"
            }
        )
        
        # Mock provider health and costs for Chinese optimization
        provider_manager.get_provider_health.return_value = {
            ProviderType.DEEPSEEK: ProviderHealth(
                provider=ProviderType.DEEPSEEK,
                status="healthy",
                latency_ms=800,
                success_rate=0.97,
                error_rate=0.03
            ),
            ProviderType.GEMINI: ProviderHealth(
                provider=ProviderType.GEMINI,
                status="healthy",
                latency_ms=700,
                success_rate=0.96,
                error_rate=0.04
            )
        }
        
        provider_manager.get_provider_costs.return_value = {
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005},
            ProviderType.GEMINI: {"cost_per_1k_tokens": 0.001}
        }
        
        selected_provider = router.select_provider(request, context)
        
        # Should prefer Chinese-optimized providers
        assert selected_provider in [ProviderType.DEEPSEEK, ProviderType.GEMINI]
    
    def test_high_volume_sales_scenario(self, comprehensive_router_setup):
        """测试高流量销售场景"""
        router, provider_manager = comprehensive_router_setup
        
        # Scenario: High-volume sales period requiring cost optimization
        context = RoutingContext(
            agent_type="sales",
            tenant_id="high_volume_brand",
            strategy=RoutingStrategy.COST_OPTIMIZED,
            volume_tier="high",
            budget_constraints={"daily_budget": 1000, "max_cost_per_request": 0.002}
        )
        
        request = LLMRequest(
            prompt="为这位客户推荐适合的套装产品",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={
                "session_type": "sales",
                "expected_volume": "high"
            }
        )
        
        # Mock cost-effective providers
        provider_manager.get_provider_costs.return_value = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.GEMINI: {"cost_per_1k_tokens": 0.001},
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005}
        }
        
        selected_provider = router.select_provider(request, context)
        
        # Should select cost-effective provider
        assert selected_provider in [ProviderType.DEEPSEEK, ProviderType.GEMINI]


class TestEmergencyRoutingScenarios:
    """测试紧急路由场景"""
    
    @pytest.fixture
    def emergency_router_setup(self):
        """紧急情况路由器设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-sonnet"]
                ),
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"]
                )
            },
            default_provider=ProviderType.ANTHROPIC,
            tenant_id="emergency_test"
        )
        
        provider_manager = Mock(spec=ProviderManager)
        router = IntelligentRouter(config, provider_manager)
        
        return router, provider_manager
    
    def test_urgent_compliance_check(self, emergency_router_setup):
        """测试紧急合规检查"""
        router, provider_manager = emergency_router_setup
        
        # Scenario: Urgent compliance check needed
        context = RoutingContext(
            agent_type="compliance",
            tenant_id="urgent_brand",
            strategy=RoutingStrategy.PERFORMANCE_FIRST,
            urgency="critical",
            metadata={"sla_requirement": "sub_500ms", "escalation_level": "high"}
        )
        
        request = LLMRequest(
            prompt="紧急检查产品广告内容是否违规",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={
                "priority": "urgent",
                "deadline": "immediate",
                "compliance_type": "advertising"
            }
        )
        
        # Mock fast provider available
        provider_manager.get_provider_health.return_value = {
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="healthy",
                latency_ms=400,  # Fast response
                success_rate=0.99,
                error_rate=0.01
            ),
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=800,  # Slower
                success_rate=0.98,
                error_rate=0.02
            )
        }
        
        selected_provider = router.select_provider(request, context)
        
        # Should select fastest provider for urgent requests
        assert selected_provider == ProviderType.ANTHROPIC
    
    def test_provider_outage_scenario(self, emergency_router_setup):
        """测试供应商故障场景"""
        router, provider_manager = emergency_router_setup
        
        context = RoutingContext(
            agent_type="sales",
            tenant_id="failover_test",
            strategy=RoutingStrategy.BALANCED
        )
        
        request = LLMRequest(
            prompt="继续为客户提供服务",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        # Mock primary provider down, backup healthy
        provider_manager.get_provider_health.return_value = {
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="unhealthy",  # Primary down
                latency_ms=999999,
                success_rate=0.0,
                error_rate=1.0
            ),
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",  # Backup working
                latency_ms=800,
                success_rate=0.98,
                error_rate=0.02
            )
        }
        
        selected_provider = router.select_provider(request, context)
        
        # Should failover to healthy provider
        assert selected_provider == ProviderType.OPENAI


class TestComplexContextRoutingScenarios:
    """测试复杂上下文路由场景"""
    
    @pytest.fixture
    def complex_router_setup(self):
        """复杂上下文路由设置"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"]
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-sonnet"]
                ),
                ProviderType.DEEPSEEK: ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    api_key="test-key",
                    models=["deepseek-chat"]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="complex_test"
        )
        
        provider_manager = Mock(spec=ProviderManager)
        router = IntelligentRouter(config, provider_manager)
        
        return router, provider_manager
    
    def test_multi_criteria_decision(self, complex_router_setup):
        """测试多标准决策"""
        router, provider_manager = complex_router_setup
        
        # Complex scenario with multiple conflicting criteria
        context = RoutingContext(
            agent_type="product",
            tenant_id="multi_criteria_brand",
            strategy=RoutingStrategy.BALANCED,
            content_language="chinese",
            customer_profile={
                "tier": "premium",
                "sensitivity": "price_conscious",
                "region": "china"
            },
            budget_constraints={"max_cost_per_request": 0.002},
            performance_requirements={"max_latency_ms": 1000}
        )
        
        request = LLMRequest(
            prompt="为VIP客户推荐高端产品，需要详细的成分分析",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={
                "customer_tier": "vip",
                "analysis_depth": "detailed",
                "language": "chinese"
            }
        )
        
        # Mock balanced provider performance
        provider_manager.get_provider_health.return_value = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=800,  # Good performance
                success_rate=0.98,
                error_rate=0.02
            ),
            ProviderType.DEEPSEEK: ProviderHealth(
                provider=ProviderType.DEEPSEEK,
                status="healthy",
                latency_ms=900,  # Acceptable performance
                success_rate=0.96,
                error_rate=0.04
            )
        }
        
        provider_manager.get_provider_costs.return_value = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},  # At budget limit
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005}  # Well under budget
        }
        
        selected_provider = router.select_provider(request, context)
        
        # Should balance all criteria effectively
        assert selected_provider in [ProviderType.OPENAI, ProviderType.DEEPSEEK]
    
    def test_context_switching_scenario(self, complex_router_setup):
        """测试上下文切换场景"""
        router, provider_manager = complex_router_setup
        
        # Scenario: Context changes during conversation
        initial_context = RoutingContext(
            agent_type="sales",
            tenant_id="context_switch_brand",
            strategy=RoutingStrategy.COST_OPTIMIZED,
            conversation_phase="initial_inquiry"
        )
        
        escalated_context = RoutingContext(
            agent_type="compliance",
            tenant_id="context_switch_brand",
            strategy=RoutingStrategy.PERFORMANCE_FIRST,
            conversation_phase="compliance_review",
            urgency="high"
        )
        
        initial_request = LLMRequest(
            prompt="询问产品基本信息",
            request_type=RequestType.CHAT,
            model="auto"
        )
        
        escalated_request = LLMRequest(
            prompt="需要进行详细的合规性检查",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={"requires_accuracy": True}
        )
        
        # Mock different optimal providers for different phases
        provider_manager.get_provider_health.return_value = {
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="healthy",
                latency_ms=500,  # Fast for compliance
                success_rate=0.99,
                error_rate=0.01
            ),
            ProviderType.DEEPSEEK: ProviderHealth(
                provider=ProviderType.DEEPSEEK,
                status="healthy",
                latency_ms=900,  # Slower but cheaper for sales
                success_rate=0.96,
                error_rate=0.04
            )
        }
        
        provider_manager.get_provider_costs.return_value = {
            ProviderType.ANTHROPIC: {"cost_per_1k_tokens": 0.003},
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005}
        }
        
        initial_provider = router.select_provider(initial_request, initial_context)
        escalated_provider = router.select_provider(escalated_request, escalated_context)
        
        # Should adapt to context changes
        # Initial phase should prefer cost-effective provider
        assert initial_provider == ProviderType.DEEPSEEK
        
        # Escalated phase should prefer performance provider
        assert escalated_provider == ProviderType.ANTHROPIC


if __name__ == "__main__":
    print("路由场景测试模块加载成功")
    print("测试覆盖: 真实场景、紧急情况、复杂上下文决策")