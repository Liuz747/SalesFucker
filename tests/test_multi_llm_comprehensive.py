"""
多LLM系统综合测试套件

该测试套件为重构后的多LLM系统提供全面的测试覆盖，
测试整合后的组件和简化后的架构。

测试覆盖:
- 整合后的供应商管理器
- 整合后的智能路由器
- 整合后的成本优化器
- 简化的重试逻辑
- 端到端集成测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.multi_llm_client import MultiLLMClient, get_multi_llm_client
from src.llm.provider_manager import ProviderManager
from src.llm.intelligent_router import IntelligentRouter, RoutingStrategy
from src.llm.cost_optimizer import CostOptimizer
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig, 
    ProviderCredentials, TenantProviderConfig
)
from src.llm.base_provider import ProviderError, RateLimitError


class TestConsolidatedProviderManager:
    """测试整合后的供应商管理器"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return GlobalProviderConfig(
            default_providers={
                "openai": ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.OPENAI,
                        api_key="test-key"
                    ),
                    is_enabled=True
                )
            }
        )
    
    @pytest.mark.asyncio
    async def test_provider_manager_initialization(self, mock_config):
        """测试供应商管理器初始化"""
        with patch.multiple(
            'src.llm.provider_manager.ProviderManager',
            _initialize_all_providers=AsyncMock(),
            _start_monitoring=AsyncMock(),
            _start_collection=AsyncMock()
        ):
            manager = ProviderManager(mock_config)
            await manager.initialize()
            
            assert manager.config == mock_config
            assert hasattr(manager, 'default_providers')
            assert hasattr(manager, 'tenant_providers')
    
    @pytest.mark.asyncio
    async def test_integrated_health_monitoring(self, mock_config):
        """测试集成的健康监控功能"""
        manager = ProviderManager(mock_config)
        
        # 测试健康监控方法存在
        assert hasattr(manager, '_start_monitoring')
        assert hasattr(manager, '_stop_monitoring')
        assert hasattr(manager, '_get_health_summary')
        assert hasattr(manager, '_get_unhealthy_providers')
    
    @pytest.mark.asyncio
    async def test_integrated_stats_collection(self, mock_config):
        """测试集成的统计收集功能"""
        manager = ProviderManager(mock_config)
        
        # 测试统计收集方法存在
        assert hasattr(manager, '_start_collection')
        assert hasattr(manager, '_stop_collection')
        assert hasattr(manager, '_get_global_stats')
        assert hasattr(manager, '_get_performance_summary')


class TestConsolidatedIntelligentRouter:
    """测试整合后的智能路由器"""
    
    @pytest.fixture
    def mock_provider_manager(self):
        """创建模拟供应商管理器"""
        manager = Mock()
        manager.get_available_providers.return_value = []
        return manager
    
    def test_router_initialization(self, mock_provider_manager):
        """测试路由器初始化"""
        router = IntelligentRouter(mock_provider_manager)
        
        # 测试集成的功能存在
        assert hasattr(router, '_apply_routing_rules')
        assert hasattr(router, '_score_providers')
        assert hasattr(router, '_select_provider')
        assert hasattr(router, 'agent_optimizations')
    
    @pytest.mark.asyncio
    async def test_routing_with_integrated_engines(self, mock_provider_manager):
        """测试使用集成引擎的路由"""
        from src.llm.base_provider import LLMRequest, RequestType
        from src.llm.intelligent_router import RoutingContext
        
        router = IntelligentRouter(mock_provider_manager)
        
        request = LLMRequest(
            request_id="test-123",
            request_type=RequestType.CHAT_COMPLETION,
            messages=[{"role": "user", "content": "test"}]
        )
        
        context = RoutingContext(
            agent_type="sales",
            tenant_id="test-tenant"
        )
        
        # 模拟空的可用供应商列表，应该抛出错误
        with pytest.raises(ProviderError, match="没有可用的供应商"):
            await router.route_request(request, context)


class TestConsolidatedCostOptimizer:
    """测试整合后的成本优化器"""
    
    def test_cost_optimizer_initialization(self):
        """测试成本优化器初始化"""
        optimizer = CostOptimizer()
        
        # 测试集成的功能存在
        assert hasattr(optimizer, '_check_budget_alerts')
        assert hasattr(optimizer, '_calculate_cost_trends')
        assert hasattr(optimizer, '_identify_optimization_opportunities')
        assert hasattr(optimizer, '_analyze_provider_switching')
        assert hasattr(optimizer, '_analyze_model_downgrading')
        assert hasattr(optimizer, '_analyze_cache_opportunities')
    
    @pytest.mark.asyncio
    async def test_integrated_cost_analysis(self):
        """测试集成的成本分析功能"""
        optimizer = CostOptimizer()
        
        # 测试空数据分析
        analysis = await optimizer.analyze_costs()
        
        assert analysis.total_cost == 0.0
        assert analysis.total_requests == 0
        assert analysis.total_tokens == 0
        assert len(analysis.optimization_opportunities) == 0


class TestMultiLLMClientIntegration:
    """测试多LLM客户端集成"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return GlobalProviderConfig(
            default_providers={
                "openai": ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.OPENAI,
                        api_key="test-key"
                    ),
                    is_enabled=True
                )
            }
        )
    
    @pytest.mark.asyncio
    async def test_client_with_consolidated_components(self, mock_config):
        """测试客户端使用整合后的组件"""
        with patch('src.llm.multi_llm_client.ProviderManager') as mock_pm, \
             patch('src.llm.multi_llm_client.IntelligentRouter') as mock_router, \
             patch('src.llm.multi_llm_client.CostOptimizer') as mock_co:
            
            client = MultiLLMClient(mock_config)
            
            # 验证使用了整合后的组件
            mock_pm.assert_called_once_with(mock_config)
            mock_router.assert_called_once()
            mock_co.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_simplified_retry_logic(self, mock_config):
        """测试简化的重试逻辑"""
        with patch('src.llm.multi_llm_client.ProviderManager') as mock_pm, \
             patch('src.llm.multi_llm_client.IntelligentRouter') as mock_router, \
             patch('src.llm.multi_llm_client.CostOptimizer') as mock_co:
            
            client = MultiLLMClient(mock_config)
            
            # 模拟路由器返回失败的供应商
            mock_provider = Mock()
            mock_provider.chat_completion = AsyncMock(
                side_effect=ProviderError("Test error", ProviderType.OPENAI, "TEST_ERR")
            )
            mock_router.return_value.route_request.return_value = mock_provider
            
            messages = [{"role": "user", "content": "test"}]
            
            with pytest.raises(ProviderError):
                await client.chat_completion(
                    messages=messages,
                    agent_type="test",
                    max_retries=1
                )
            
            # 验证重试逻辑被调用
            assert mock_provider.chat_completion.call_count == 2  # 初始 + 1次重试


class TestSystemHealthAndMonitoring:
    """测试系统健康和监控"""
    
    @pytest.mark.asyncio
    async def test_global_health_reporting(self):
        """测试全局健康报告"""
        with patch('src.llm.multi_llm_client.get_multi_llm_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_global_stats.return_value = {
                "total_requests": 100,
                "successful_requests": 95,
                "error_rate": 5.0
            }
            mock_get_client.return_value = mock_client
            
            client = await get_multi_llm_client()
            stats = await client.get_global_stats()
            
            assert "total_requests" in stats
            assert "successful_requests" in stats
            assert "error_rate" in stats


class TestUnifiedBaseAgentArchitecture:
    """测试统一的BaseAgent架构"""
    
    def test_unified_base_agent_import(self):
        """确认统一BaseAgent导入正常工作"""
        try:
            from src.agents.core.base import BaseAgent
            from src.llm.intelligent_router import RoutingStrategy
            from src.llm.provider_config import GlobalProviderConfig
            
            # 如果能导入说明统一架构成功
            assert True
        except ImportError as e:
            pytest.fail(f"Unified BaseAgent imports failed: {e}")
    
    def test_base_agent_mas_llm_features(self):
        """测试BaseAgent的MAS多LLM功能"""
        from src.agents.core.base import BaseAgent
        from src.llm.intelligent_router import RoutingStrategy
        
        # MAS架构：所有智能体都具备LLM能力
        sales_agent = BaseAgent(
            agent_id="sales_test",
            tenant_id="test_tenant",
            routing_strategy=RoutingStrategy.SALES_OPTIMIZED
        )
        
        assert sales_agent.multi_llm_available == True  # 架构变更
        assert sales_agent.agent_type == "sales"
        assert sales_agent.routing_strategy == RoutingStrategy.SALES_OPTIMIZED
        assert hasattr(sales_agent, 'llm_stats')
        assert hasattr(sales_agent, 'llm_preferences')
        
        # 测试配置自动加载
        product_agent = BaseAgent(
            agent_id="product_expert_test",
            tenant_id="test_tenant"
        )
        
        assert product_agent.agent_type == "product"
        # 自动加载产品智能体的偏好配置
        assert product_agent.llm_preferences.get("temperature") == 0.5  # 来自配置文件
    
    def test_mas_agent_preference_loading(self):
        """测试MAS智能体偏好配置加载"""
        from src.agents.core.base import BaseAgent
        from src.llm.agent_preferences import get_agent_preferences
        
        # 测试智能体类型配置自动加载
        compliance_agent = BaseAgent(
            agent_id="compliance_review_test",
            tenant_id="test_tenant"
        )
        
        # 验证合规智能体的高精度配置
        assert compliance_agent.agent_type == "compliance"
        assert compliance_agent.llm_preferences.get("temperature") == 0.3  # 高精度
        assert compliance_agent.llm_preferences.get("quality_threshold") == 0.9
        
        # 验证配置一致性
        direct_config = get_agent_preferences("compliance")
        assert compliance_agent.llm_preferences == direct_config
    
    def test_no_more_micro_modules_and_deprecated_files(self):
        """确认微模块目录和弃用文件已被移除"""
        import os
        
        base_path = "/Users/preszheng/Desktop/HM/mas-v0.2/src/llm"
        
        # 已移除的微模块目录
        obsolete_dirs = [
            "failover_system",
            "cost_optimizer_modules", 
            "intelligent_router_modules",
            "provider_manager_modules",
            "enhanced_base_agent_modules"
        ]
        
        for dir_name in obsolete_dirs:
            dir_path = os.path.join(base_path, dir_name)
            assert not os.path.exists(dir_path), f"Directory {dir_name} should have been removed"
        
        # 确认弃用文件已被删除
        deprecated_file = os.path.join(base_path, "enhanced_base_agent.py")
        assert not os.path.exists(deprecated_file), "enhanced_base_agent.py should have been removed"
    
    def test_consolidated_llm_imports_work(self):
        """确认整合后的LLM导入正常工作"""
        try:
            from src.llm.multi_llm_client import MultiLLMClient
            from src.llm.provider_manager import ProviderManager
            from src.llm.intelligent_router import IntelligentRouter
            from src.llm.cost_optimizer import CostOptimizer
            
            # 测试新的统一架构
            from src.agents.core.base import BaseAgent
            
            # 如果能导入说明整合成功
            assert True
        except ImportError as e:
            pytest.fail(f"Consolidated imports failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])