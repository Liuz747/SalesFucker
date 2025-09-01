"""
多LLM供应商系统核心测试套件

该测试套件为多LLM供应商系统提供核心测试覆盖，专注于:
- 供应商抽象层和基础接口测试
- 供应商配置系统测试
- 多LLM客户端集成测试

更多专业测试请参见:
- test_provider_implementations.py (各供应商具体实现)
- test_provider_error_handling.py (错误处理和弹性)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from infra.runtimes.providers.base import BaseProvider
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.entities.providers import ProviderType
from infra.runtimes.providers import OpenAIProvider, AnthropicProvider
from infra.runtimes.client import LLMClient
from infra.runtimes.config import LLMConfig

# Note: Simplified provider system - many complex features removed for MVP


class TestBaseProviderInterface:
    """测试基础供应商接口和抽象层功能"""
    
    def test_llm_request_creation(self):
        """测试LLM请求对象创建和验证"""
        request = LLMRequest(
            prompt="测试提示信息",
            request_type=RequestType.CHAT,
            model="gpt-4",
            max_tokens=100,
            temperature=0.7,
            metadata={"agent_type": "sales"}
        )
        
        assert request.prompt == "测试提示信息"
        assert request.request_type == RequestType.CHAT
        assert request.model == "gpt-4"
        assert request.max_tokens == 100
        assert request.temperature == 0.7
        assert request.metadata["agent_type"] == "sales"
        assert request.created_at is not None
    
    def test_llm_response_creation(self):
        """测试LLM响应对象创建和属性"""
        response = LLMResponse(
            content="测试响应内容",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.002,
            input_tokens=50,
            output_tokens=25,
            latency_ms=1200,
            metadata={"quality_score": 0.95}
        )
        
        assert response.content == "测试响应内容"
        assert response.model == "gpt-4"
        assert response.provider == ProviderType.OPENAI
        assert response.cost == 0.002
        assert response.input_tokens == 50
        assert response.output_tokens == 25
        assert response.latency_ms == 1200
        assert response.metadata["quality_score"] == 0.95
        assert response.created_at is not None
    
    def test_provider_health_status(self):
        """测试供应商健康状态对象"""
        health = ProviderHealth(
            provider=ProviderType.OPENAI,
            status="healthy",
            last_check=datetime.now(),
            latency_ms=800,
            error_rate=0.02,
            success_rate=0.98,
            metadata={"last_error": None}
        )
        
        assert health.provider == ProviderType.OPENAI
        assert health.status == "healthy"
        assert health.latency_ms == 800
        assert health.error_rate == 0.02
        assert health.success_rate == 0.98
        assert health.is_healthy()
    


class TestProviderConfigurations:
    """测试供应商配置系统"""
    
    def test_provider_config_creation(self):
        """测试单个供应商配置创建"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            models=["gpt-4", "gpt-3.5-turbo"],
            capabilities=[ModelCapability.CHAT, ModelCapability.EMBEDDING],
            rate_limit=1000,
            timeout=30,
            enabled=True
        )
        
        assert config.provider_type == ProviderType.OPENAI
        assert config.api_key == "test-key"
        assert "gpt-4" in config.models
        assert ModelCapability.CHAT in config.capabilities
        assert config.rate_limit == 1000
        assert config.enabled is True
    
    def test_global_provider_config(self):
        """测试全局供应商配置"""
        openai_config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="openai-key",
            models=["gpt-4", "gpt-3.5-turbo"],
            capabilities=[ModelCapability.CHAT]
        )
        
        anthropic_config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="anthropic-key", 
            models=["claude-3-opus", "claude-3-sonnet"],
            capabilities=[ModelCapability.CHAT]
        )
        
        global_config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: openai_config,
                ProviderType.ANTHROPIC: anthropic_config
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="test_tenant"
        )
        
        assert len(global_config.providers) == 2
        assert global_config.default_provider == ProviderType.OPENAI
        assert global_config.tenant_id == "test_tenant"
        assert ProviderType.OPENAI in global_config.providers
        assert ProviderType.ANTHROPIC in global_config.providers
    


# 注意: 各供应商具体实现测试已移至 test_provider_implementations.py


class TestProviderManager:
    """测试供应商管理器功能"""
    
    @pytest.fixture
    def multi_provider_config(self):
        """多供应商配置fixture"""
        configs = {}
        for provider_type in [ProviderType.OPENAI, ProviderType.ANTHROPIC, 
                             ProviderType.GEMINI, ProviderType.DEEPSEEK]:
            configs[provider_type] = ProviderConfig(
                provider_type=provider_type,
                api_key=f"{provider_type.value}-key",
                models=[f"{provider_type.value}-model"],
                capabilities=[ModelCapability.CHAT]
            )
        
        return GlobalProviderConfig(
            providers=configs,
            default_provider=ProviderType.OPENAI,
            tenant_id="test_tenant"
        )
    
    def test_provider_manager_initialization(self, multi_provider_config):
        """测试供应商管理器初始化"""
        manager = ProviderManager(multi_provider_config)
        
        assert len(manager.providers) == 4
        assert ProviderType.OPENAI in manager.providers
        assert ProviderType.ANTHROPIC in manager.providers
        assert ProviderType.GEMINI in manager.providers
        assert ProviderType.DEEPSEEK in manager.providers
    
    def test_get_provider_by_type(self, multi_provider_config):
        """测试按类型获取供应商"""
        manager = ProviderManager(multi_provider_config)
        
        openai_provider = manager.get_provider(ProviderType.OPENAI)
        assert openai_provider is not None
        assert openai_provider.provider_type == ProviderType.OPENAI
        
        anthropic_provider = manager.get_provider(ProviderType.ANTHROPIC)
        assert anthropic_provider is not None
        assert anthropic_provider.provider_type == ProviderType.ANTHROPIC
    
    


class TestMultiLLMClientIntegration:
    """测试多LLM客户端集成功能"""
    
    @pytest.fixture
    def full_config(self):
        """完整配置fixture"""
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
            default_provider=ProviderType.OPENAI,
            tenant_id="integration_test"
        )
    
    def test_multi_llm_client_initialization(self, full_config):
        """测试多LLM客户端初始化"""
        client = MultiLLMClient(full_config)
        
        assert client.config == full_config
        assert client.provider_manager is not None
        assert client.intelligent_router is not None
        assert client.failover_system is not None
        assert client.cost_optimizer is not None
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_provider_selection(self, full_config):
        """测试带供应商选择的聊天完成"""
        client = MultiLLMClient(full_config)
        
        # Mock provider managers and routing
        mock_provider = Mock()
        mock_provider.chat_completion = AsyncMock(return_value=LLMResponse(
            content="测试响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.001,
            input_tokens=10,
            output_tokens=15,
            latency_ms=800
        ))
        
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider', return_value=mock_provider):
                request = LLMRequest(
                    prompt="测试提示",
                    request_type=RequestType.CHAT,
                    model="gpt-4"
                )
                
                response = await client.chat_completion(request)
                
                assert response.content == "测试响应"
                assert response.provider == ProviderType.OPENAI
                assert response.cost == 0.001
                mock_provider.chat_completion.assert_called_once_with(request)


# 注意: 错误处理和弹性测试已移至 test_provider_error_handling.py


if __name__ == "__main__":
    async def run_core_provider_tests():
        print("运行核心多LLM供应商测试...")
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            models=["gpt-4"],
            capabilities=[ModelCapability.CHAT]
        )
        print(f"配置创建成功: {config.provider_type}")
        global_config = GlobalProviderConfig(
            providers={ProviderType.OPENAI: config},
            default_provider=ProviderType.OPENAI,
            tenant_id="test"
        )
        manager = ProviderManager(global_config)
        print(f"供应商管理器初始化成功: {len(manager.providers)} 个供应商")
        print("核心供应商测试完成!")
    
    asyncio.run(run_core_provider_tests())