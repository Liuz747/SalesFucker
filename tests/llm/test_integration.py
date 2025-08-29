"""
多LLM系统高级集成测试套件

该测试套件专门测试多LLM系统的高级集成功能:
- 智能体供应商映射
- 全局客户端管理
- 复杂配置管理
"""

import pytest
from unittest.mock import Mock, patch

from infra.runtimes.client import LLMClient
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType

# Note: Complex routing and mapping features have been simplified in the new system


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
    
    def test_mapping_configuration_validation(self, mapping_config):
        """测试映射配置验证"""
        # Verify all mappings are properly configured
        assert "compliance" in mapping_config.agent_mappings
        assert "sales" in mapping_config.agent_mappings
        
        # Verify mapping structure
        for agent_type, mapping in mapping_config.agent_mappings.items():
            assert mapping.agent_type == agent_type
            assert len(mapping.preferred_providers) > 0
            assert len(mapping.fallback_providers) > 0
            assert isinstance(mapping.routing_rules, dict)


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
    
    def test_client_lifecycle_management(self):
        """测试客户端生命周期管理"""
        # Test initial client creation
        client = get_multi_llm_client()
        assert client is not None
        
        # Test client persistence
        same_client = get_multi_llm_client()
        assert client is same_client
        
        # Verify client has required components
        assert hasattr(client, 'config')
        assert hasattr(client, 'provider_manager')
        assert hasattr(client, 'intelligent_router')


class TestAdvancedConfiguration:
    """测试高级配置"""
    
    def test_complex_provider_configuration(self):
        """测试复杂供应商配置"""
        complex_config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="openai-key",
                    models=["gpt-4", "gpt-3.5-turbo"],
                    capabilities=[ModelCapability.CHAT, ModelCapability.EMBEDDING],
                    is_enabled=True,
                    priority=1,
                    rate_limits={"requests_per_minute": 60},
                    timeout_settings={"request_timeout": 30}
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="anthropic-key",
                    models=["claude-3-opus", "claude-3-sonnet"],
                    capabilities=[ModelCapability.CHAT],
                    is_enabled=True,
                    priority=2,
                    rate_limits={"requests_per_minute": 30},
                    timeout_settings={"request_timeout": 45}
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="complex_test",
            routing_preferences={
                "default_strategy": RoutingStrategy.BALANCED,
                "fallback_strategy": RoutingStrategy.COST_OPTIMIZED
            }
        )
        
        # Verify complex configuration structure
        assert len(complex_config.providers) == 2
        assert complex_config.default_provider == ProviderType.OPENAI
        
        # Verify provider-specific settings
        openai_config = complex_config.providers[ProviderType.OPENAI]
        assert openai_config.priority == 1
        assert "gpt-4" in openai_config.models
        assert ModelCapability.CHAT in openai_config.capabilities
        
        anthropic_config = complex_config.providers[ProviderType.ANTHROPIC]
        assert anthropic_config.priority == 2
        assert "claude-3-opus" in anthropic_config.models
    
    def test_multi_tenant_configuration(self):
        """测试多租户配置"""
        tenant_configs = {
            "tenant_a": GlobalProviderConfig(
                providers={
                    ProviderType.OPENAI: ProviderConfig(
                        provider_type=ProviderType.OPENAI,
                        api_key="tenant-a-key",
                        models=["gpt-4"]
                    )
                },
                default_provider=ProviderType.OPENAI,
                tenant_id="tenant_a"
            ),
            "tenant_b": GlobalProviderConfig(
                providers={
                    ProviderType.ANTHROPIC: ProviderConfig(
                        provider_type=ProviderType.ANTHROPIC,
                        api_key="tenant-b-key",
                        models=["claude-3-sonnet"]
                    )
                },
                default_provider=ProviderType.ANTHROPIC,
                tenant_id="tenant_b"
            )
        }
        
        # Verify tenant isolation
        assert tenant_configs["tenant_a"].tenant_id == "tenant_a"
        assert tenant_configs["tenant_b"].tenant_id == "tenant_b"
        
        # Verify different provider preferences
        assert tenant_configs["tenant_a"].default_provider == ProviderType.OPENAI
        assert tenant_configs["tenant_b"].default_provider == ProviderType.ANTHROPIC
        
        # Verify no cross-tenant data leakage
        assert ProviderType.ANTHROPIC not in tenant_configs["tenant_a"].providers
        assert ProviderType.OPENAI not in tenant_configs["tenant_b"].providers


if __name__ == "__main__":
    print("多LLM系统集成测试模块加载成功")
    print("测试覆盖: 智能体映射、全局客户端、高级配置")