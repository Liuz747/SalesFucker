"""
多LLM系统性能测试套件（重构版）

该测试套件提供精简的性能测试，专注于:
- 基础并发性能验证
- 响应时间基准测试
- 内存使用基本监控
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.multi_llm_client import MultiLLMClient
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    ModelCapability
)
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType,
    ProviderError, RateLimitError
)


class TestBasicPerformance:
    """基础性能测试"""
    
    @pytest.fixture
    def perf_config(self):
        """性能测试配置"""
        return GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"],
                    capabilities=[ModelCapability.CHAT],
                    rate_limit=2000,
                    timeout=10
                ),
                ProviderType.ANTHROPIC: ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key="test-key",
                    models=["claude-3-sonnet"],
                    capabilities=[ModelCapability.CHAT],
                    rate_limit=1500,
                    timeout=15
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="perf_test"
        )
    
    @pytest.mark.asyncio
    async def test_single_request_latency(self, perf_config):
        """测试单个请求延迟"""
        client = MultiLLMClient(perf_config)
        
        request = LLMRequest(
            prompt="性能测试请求",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        # Mock快速响应
        mock_response = LLMResponse(
            content="性能测试响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.001,
            input_tokens=5,
            output_tokens=8,
            latency_ms=500
        )
        
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(return_value=mock_response)
                mock_get_provider.return_value = mock_provider
                
                # 测量执行时间
                start_time = time.time()
                response = await client.chat_completion(request)
                end_time = time.time()
                
                execution_time_ms = (end_time - start_time) * 1000
                
                # 验证响应
                assert response.content == "性能测试响应"
                assert response.latency_ms == 500
                
                # 验证执行时间在合理范围内
                assert execution_time_ms < 100
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, perf_config):
        """测试并发请求性能"""
        client = MultiLLMClient(perf_config)
        
        # 创建多个并发请求
        num_requests = 5
        requests = [
            LLMRequest(
                prompt=f"并发请求 {i}",
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            for i in range(num_requests)
        ]
        
        # Mock响应
        mock_responses = [
            LLMResponse(
                content=f"并发响应 {i}",
                model="gpt-4",
                provider=ProviderType.OPENAI,
                cost=0.001,
                input_tokens=5,
                output_tokens=8,
                latency_ms=400 + i * 50
            )
            for i in range(num_requests)
        ]
        
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(side_effect=mock_responses)
                mock_get_provider.return_value = mock_provider
                
                # 测量并发执行时间
                start_time = time.time()
                results = await asyncio.gather(
                    *[client.chat_completion(req) for req in requests],
                    return_exceptions=True
                )
                end_time = time.time()
                
                total_time_ms = (end_time - start_time) * 1000
                
                # 验证所有请求成功
                assert len(results) == num_requests
                for i, result in enumerate(results):
                    assert not isinstance(result, Exception)
                    assert result.content == f"并发响应 {i}"
                
                assert total_time_ms < 1000  # 验证并发执行效率
    
    @pytest.mark.asyncio
    async def test_provider_switching_latency(self, perf_config):
        """测试供应商切换延迟"""
        client = MultiLLMClient(perf_config)
        
        request = LLMRequest(
            prompt="供应商切换测试",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        # Mock两个不同供应商的响应
        openai_response = LLMResponse(
            content="OpenAI响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.002,
            input_tokens=6,
            output_tokens=10,
            latency_ms=500
        )
        
        anthropic_response = LLMResponse(
            content="Anthropic响应",
            model="claude-3-sonnet",
            provider=ProviderType.ANTHROPIC,
            cost=0.003,
            input_tokens=6,
            output_tokens=10,
            latency_ms=600
        )
        
        # 测试第一个供应商
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_openai_provider = Mock()
                mock_openai_provider.chat_completion = AsyncMock(return_value=openai_response)
                mock_get_provider.return_value = mock_openai_provider
                
                start_time = time.time()
                response1 = await client.chat_completion(request)
                switch_time_1 = time.time() - start_time
                
                assert response1.provider == ProviderType.OPENAI
        
        # 测试切换到第二个供应商
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.ANTHROPIC):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_anthropic_provider = Mock()
                mock_anthropic_provider.chat_completion = AsyncMock(return_value=anthropic_response)
                mock_get_provider.return_value = mock_anthropic_provider
                
                start_time = time.time()
                response2 = await client.chat_completion(request)
                switch_time_2 = time.time() - start_time
                
                assert response2.provider == ProviderType.ANTHROPIC
        
        # 验证切换没有显著额外开销
        time_diff = abs(switch_time_2 - switch_time_1) * 1000
        assert time_diff < 50
    
    def test_memory_usage_basic(self, perf_config):
        """测试基本内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建客户端
        client = MultiLLMClient(perf_config)
        
        # 创建多个请求对象
        requests = [
            LLMRequest(
                prompt=f"内存测试请求 {i}" * 10,  # 较长的文本
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            for i in range(100)
        ]
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        # 验证内存增长在合理范围内
        assert memory_increase < 50
        del client, requests
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, perf_config):
        """测试错误处理性能"""
        client = MultiLLMClient(perf_config)
        
        request = LLMRequest(
            prompt="错误处理测试",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        # Mock提供商错误
        with patch.object(client.intelligent_router, 'select_provider', return_value=ProviderType.OPENAI):
            with patch.object(client.provider_manager, 'get_provider') as mock_get_provider:
                mock_provider = Mock()
                mock_provider.chat_completion = AsyncMock(side_effect=ProviderError(
                    message="Provider error",
                    provider=ProviderType.OPENAI
                ))
                mock_get_provider.return_value = mock_provider
                
                # 测量错误处理时间
                start_time = time.time()
                try:
                    await client.chat_completion(request)
                    assert False, "Should have raised ProviderError"
                except ProviderError:
                    pass
                end_time = time.time()
                
                error_handling_time_ms = (end_time - start_time) * 1000
                
                # 验证错误处理速度
                assert error_handling_time_ms < 100


if __name__ == "__main__":
    async def run_performance_tests():
        print("运行基础性能测试...")
        
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
            tenant_id="perf_test"
        )
        
        client = MultiLLMClient(config)
        print("性能测试客户端初始化成功")
        print("基础性能测试完成!")
    
    asyncio.run(run_performance_tests())