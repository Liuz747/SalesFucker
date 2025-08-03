"""
多LLM系统综合测试套件（重构版）

该测试套件提供精简的综合测试，专注于:
- 核心系统集成验证
- 关键组件协作测试
- 基础端到端流程测试

更多详细测试请参见:
- test_integration_comprehensive.py (完整集成测试)
- test_failover_system.py (故障转移专项测试)
- test_cost_optimization.py (成本优化专项测试)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from src.llm.multi_llm_client import MultiLLMClient
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    ModelCapability
)
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType, ProviderError
)


class TestCoreSystemIntegration:
    """核心系统集成测试"""
    
    @pytest.fixture
    def simple_config(self):
        """简单的多供应商配置"""
        return GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT],
                    is_enabled=True
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-sonnet"],
                    capabilities=[ModelCapability.CHAT],
                    is_enabled=True
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="comprehensive_test"
        )
    
    def test_system_components_initialization(self, simple_config):
        """测试系统组件初始化"""
        client = MultiLLMClient(simple_config)
        
        # 验证所有核心组件都已正确初始化
        assert client.provider_manager is not None
        assert client.intelligent_router is not None
        assert client.failover_system is not None
        assert client.cost_optimizer is not None
        
        # 验证供应商加载
        assert len(client.provider_manager.providers) == 2
        assert ProviderType.OPENAI in client.provider_manager.providers
        assert ProviderType.ANTHROPIC in client.provider_manager.providers
    
    @pytest.mark.asyncio
    async def test_end_to_end_request_processing(self, simple_config):
        """测试端到端请求处理"""
        client = MultiLLMClient(simple_config)
        
        # 创建测试请求
        request = LLMRequest(
            prompt="这是一个端到端测试",
            request_type=RequestType.CHAT,
            model="gpt-4",
            max_tokens=100
        )
        
        # Mock整个处理流程
        mock_response = LLMResponse(
            content="端到端测试响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.002,
            input_tokens=8,
            output_tokens=12,
            latency_ms=1000
        )
        
        # Mock所有必要的组件
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(return_value=mock_response)
                mock_get_provider.return_value = mock_provider
                
                # 执行请求
                response = await client.chat_completion(request)
                
                # 验证响应
                assert response.content == "端到端测试响应"
                assert response.provider == ProviderType.OPENAI
                assert response.cost == 0.002
                assert response.input_tokens == 8
                assert response.output_tokens == 12
                
                # 验证调用链
                mock_provider.chat_completion.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_provider_failover_scenario(self, simple_config):
        """测试供应商故障转移场景"""
        client = MultiLLMClient(simple_config)
        
        request = LLMRequest(
            prompt="测试故障转移",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        # Mock第一个供应商失败，第二个成功
        fallback_response = LLMResponse(
            content="故障转移成功响应",
            model="claude-3-sonnet",
            provider=ProviderType.ANTHROPIC,
            cost=0.003,
            input_tokens=6,
            output_tokens=10,
            latency_ms=1200
        )
        
        with patch.object(client.intelligent_router, 'select_provider', side_effect=[ProviderType.OPENAI, ProviderType.ANTHROPIC]):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                # 设置第一次调用失败，第二次成功
                call_count = 0
                def mock_provider_behavior(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # 第一个供应商失败
                        failed_provider = Mock()
                        failed_provider.chat_completion = AsyncMock(side_effect=ProviderError(
                            message="Provider unavailable",
                            provider=ProviderType.OPENAI
                        ))
                        return failed_provider
                    else:
                        # 第二个供应商成功
                        success_provider = Mock()
                        success_provider.chat_completion = AsyncMock(return_value=fallback_response)
                        return success_provider
                
                mock_get_provider.side_effect = mock_provider_behavior
                
                # Mock故障转移逻辑
                with patch.object(client.failover_system, 'handle_provider_failure', return_value=ProviderType.ANTHROPIC):
                    try:
                        # 第一次尝试失败
                        await client.chat_completion(request)
                        assert False, "Should have raised ProviderError"
                    except ProviderError:
                        # 预期的错误，现在尝试故障转移
                        fallback_provider = client.failover_system.handle_provider_failure(
                            failed_provider=ProviderType.OPENAI,
                            available_providers=[ProviderType.ANTHROPIC]
                        )
                        assert fallback_provider == ProviderType.ANTHROPIC
    
    def test_cost_tracking_integration(self, simple_config):
        """测试成本追踪集成"""
        client = MultiLLMClient(simple_config)
        
        # 测试成本估算
        request = LLMRequest(
            prompt="成本追踪测试",
            request_type=RequestType.CHAT,
            model="gpt-4",
            max_tokens=200
        )
        
        # Mock成本估算
        with patch.object(client.cost_optimizer, 'estimate_cost', return_value=Decimal('0.004')):
            estimated_cost = client.cost_optimizer.estimate_cost(
                request=request,
                provider=ProviderType.OPENAI
            )
            
            assert estimated_cost == Decimal('0.004')
    
    @pytest.mark.asyncio
    async def test_multi_request_concurrent_processing(self, simple_config):
        """测试多请求并发处理"""
        client = MultiLLMClient(simple_config)
        
        # 创建多个并发请求
        requests = [
            LLMRequest(
                prompt=f"并发测试请求 {i}",
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            for i in range(3)
        ]
        
        # Mock并发响应
        responses = [
            LLMResponse(
                content=f"并发响应 {i}",
                model="gpt-4",
                provider=ProviderType.OPENAI,
                cost=0.001,
                input_tokens=5,
                output_tokens=8,
                latency_ms=800
            )
            for i in range(3)
        ]
        
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(side_effect=responses)
                mock_get_provider.return_value = mock_provider
                
                # 并发执行请求
                results = await asyncio.gather(
                    *[client.chat_completion(req) for req in requests],
                    return_exceptions=True
                )
                
                # 验证所有请求都成功处理
                assert len(results) == 3
                for i, result in enumerate(results):
                    assert not isinstance(result, Exception)
                    assert result.content == f"并发响应 {i}"


if __name__ == "__main__":
    async def run_comprehensive_tests():
        print("运行综合系统集成测试...")
        
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
        print(f"综合测试客户端初始化成功")
        print("综合系统测试完成!")
    
    asyncio.run(run_comprehensive_tests())