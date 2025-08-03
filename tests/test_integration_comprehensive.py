"""
多LLM系统集成测试套件（综合版本重构）

该测试套件提供核心集成测试，专注于:
- 多供应商基础集成测试
- 客户端初始化和配置测试
- 基本工作流程验证

更多专业测试请参见:
- test_failover_integration.py (故障转移测试)
- test_cost_optimization_integration.py (成本优化测试)
- test_multi_tenant_integration.py (多租户测试)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from src.llm.multi_llm_client import MultiLLMClient, get_multi_llm_client
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    AgentProviderMapping, ModelCapability, ProviderCredentials
)
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType, 
    ProviderError, RateLimitError, AuthenticationError
)
from src.llm.intelligent_router import RoutingStrategy, RoutingContext
from src.llm.cost_optimizer import CostOptimizer
from src.llm.failover_system import FailoverSystem
from src.llm.provider_manager import ProviderManager


class TestBasicMultiLLMIntegration:
    """基础多LLM系统集成测试"""
    
    @pytest.fixture
    def basic_config(self):
        """基础多供应商配置"""
        return GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-openai-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT],
                    is_enabled=True,
                    priority=1
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-anthropic-key",
                    models=["claude-3-sonnet"],
                    capabilities=[ModelCapability.CHAT],
                    is_enabled=True,
                    priority=2
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="integration_test"
        )
    
    def test_multi_llm_client_initialization(self, basic_config):
        """测试多LLM客户端初始化"""
        client = MultiLLMClient(basic_config)
        
        assert client.config == basic_config
        assert client.provider_manager is not None
        assert client.intelligent_router is not None
        assert client.failover_system is not None
        assert client.cost_optimizer is not None
        
        # 验证供应商数量
        assert len(client.provider_manager.providers) == 2
        assert ProviderType.OPENAI in client.provider_manager.providers
        assert ProviderType.ANTHROPIC in client.provider_manager.providers
    
    @pytest.mark.asyncio
    async def test_basic_chat_completion_flow(self, basic_config):
        """测试基础聊天完成流程"""
        client = MultiLLMClient(basic_config)
        
        # Mock provider response
        mock_response = LLMResponse(
            content="这是一个测试响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.001,
            input_tokens=10,
            output_tokens=15,
            latency_ms=800
        )
        
        # Mock the provider and router
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(return_value=mock_response)
                mock_get_provider.return_value = mock_provider
                
                request = LLMRequest(
                    prompt="测试提示",
                    request_type=RequestType.CHAT,
                    model="gpt-4"
                )
                
                response = await client.chat_completion(request)
                
                assert response.content == "这是一个测试响应"
                assert response.provider == ProviderType.OPENAI
                assert response.cost == 0.001
                mock_provider.chat_completion.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_provider_selection_logic(self, basic_config):
        """测试供应商选择逻辑"""
        client = MultiLLMClient(basic_config)
        
        # Test routing context creation
        request = LLMRequest(
            prompt="测试智能路由",
            request_type=RequestType.CHAT,
            model="gpt-4",
            metadata={
                "agent_type": "sales",
                "priority": "high",
                "language": "chinese"
            }
        )
        
        # Mock router behavior
        with patch.object(client.intelligent_router, 'select_provider') as mock_select:
            mock_select.return_value = ProviderType.OPENAI
            
            # Create routing context
            routing_context = RoutingContext(
                request=request,
                available_providers=[ProviderType.OPENAI, ProviderType.ANTHROPIC],
                strategy=RoutingStrategy.COST_OPTIMIZED,
                metadata=request.metadata
            )
            
            selected_provider = client.intelligent_router.select_provider(routing_context)
            assert selected_provider == ProviderType.OPENAI
            mock_select.assert_called_once()
    
    def test_cost_optimizer_integration(self, basic_config):
        """测试成本优化器集成"""
        client = MultiLLMClient(basic_config)
        
        # Test cost calculation
        request = LLMRequest(
            prompt="测试成本计算" * 100,  # Long prompt for cost calculation
            request_type=RequestType.CHAT,
            model="gpt-4",
            max_tokens=500
        )
        
        # Mock cost calculation
        estimated_cost = client.cost_optimizer.estimate_cost(
            request=request,
            provider=ProviderType.OPENAI
        )
        
        assert isinstance(estimated_cost, (float, Decimal))
        assert estimated_cost > 0
    
    def test_failover_system_integration(self, basic_config):
        """测试故障转移系统集成"""
        client = MultiLLMClient(basic_config)
        
        # Test failover provider identification
        available_providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        failed_provider = ProviderType.OPENAI
        
        failover_providers = client.failover_system.get_failover_providers(
            failed_provider=failed_provider,
            available_providers=available_providers
        )
        
        assert ProviderType.ANTHROPIC in failover_providers
        assert ProviderType.OPENAI not in failover_providers


class TestAgentProviderMapping:
    """测试智能体供应商映射"""
    
    @pytest.fixture
    def mapping_config(self):
        """包含智能体映射的配置"""
        return GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="openai-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="anthropic-key",
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
                ),
                "sales": AgentProviderMapping(
                    agent_type="sales",
                    preferred_providers=[ProviderType.OPENAI],
                    fallback_providers=[ProviderType.ANTHROPIC],
                    routing_rules={"priority": "speed"}
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="mapping_test"
        )
    
    def test_agent_specific_provider_selection(self, mapping_config):
        """测试智能体特定供应商选择"""
        client = MultiLLMClient(mapping_config)
        
        # Test compliance agent mapping
        compliance_mapping = mapping_config.agent_mappings["compliance"]
        assert compliance_mapping.agent_type == "compliance"
        assert ProviderType.ANTHROPIC in compliance_mapping.preferred_providers
        assert ProviderType.OPENAI in compliance_mapping.fallback_providers
        
        # Test sales agent mapping
        sales_mapping = mapping_config.agent_mappings["sales"]
        assert sales_mapping.agent_type == "sales"
        assert ProviderType.OPENAI in sales_mapping.preferred_providers
        assert ProviderType.ANTHROPIC in sales_mapping.fallback_providers
    
    @pytest.mark.asyncio
    async def test_agent_routing_with_mapping(self, mapping_config):
        """测试带映射的智能体路由"""
        client = MultiLLMClient(mapping_config)
        
        # Create request with agent context
        request = LLMRequest(
            prompt="审核这个内容是否符合规定",
            request_type=RequestType.CHAT,
            model="claude-3-sonnet",
            metadata={"agent_type": "compliance"}
        )
        
        # Mock the routing with agent mapping
        with patch.object(client.intelligent_router, 'select_provider_for_agent') as mock_select:
            mock_select.return_value = ProviderType.ANTHROPIC
            
            selected_provider = client.intelligent_router.select_provider_for_agent(
                agent_type="compliance",
                request=request,
                mapping=mapping_config.agent_mappings["compliance"]
            )
            
            assert selected_provider == ProviderType.ANTHROPIC
            mock_select.assert_called_once()


class TestMultiLLMGlobalClient:
    """测试全局多LLM客户端"""
    
    def test_global_client_singleton(self):
        """测试全局客户端单例模式"""
        # Test that get_multi_llm_client returns the same instance
        client1 = get_multi_llm_client()
        client2 = get_multi_llm_client()
        
        assert client1 is client2
        assert isinstance(client1, MultiLLMClient)
    
    @pytest.mark.asyncio
    async def test_global_client_configuration_update(self):
        """测试全局客户端配置更新"""
        client = get_multi_llm_client()
        
        # Test configuration update
        new_config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="updated-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="updated_tenant"
        )
        
        # Mock configuration update
        with patch.object(client, 'update_config') as mock_update:
            client.update_config(new_config)
            mock_update.assert_called_once_with(new_config)


if __name__ == "__main__":
    async def run_integration_tests():
        print("运行多LLM系统集成测试...")
        
        # Test basic configuration
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="test"
        )
        
        client = MultiLLMClient(config)
        print(f"客户端初始化成功: {len(client.provider_manager.providers)} 个供应商")
        print("集成测试完成!")
    
    asyncio.run(run_integration_tests())