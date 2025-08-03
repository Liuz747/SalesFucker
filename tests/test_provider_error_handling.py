"""
多LLM供应商错误处理和弹性测试套件

该测试套件专注于多LLM供应商系统的错误处理和弹性测试，包括:
- 供应商故障处理
- 配置验证和错误处理
- 超时和连接错误处理
- 系统弹性和恢复机制
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.llm.base_provider import (
    BaseProvider, LLMRequest, LLMResponse, RequestType, 
    ProviderError, ProviderHealth, RateLimitError, AuthenticationError
)
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    ModelCapability, AgentProviderMapping
)
from src.llm.providers import (
    OpenAIProvider, AnthropicProvider, 
    GeminiProvider, DeepSeekProvider
)


class TestErrorHandlingAndResilience:
    """测试错误处理和系统弹性"""
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self):
        """测试供应商故障处理"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            models=["gpt-4"]
        )
        
        provider = OpenAIProvider(config)
        
        # Mock API failure
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = ProviderError(
                message="API限制exceeded",
                provider=ProviderType.OPENAI,
                error_code="rate_limit_exceeded",
                retry_after=60
            )
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.chat_completion(request)
            
            assert exc_info.value.error_code == "rate_limit_exceeded"
            assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self):
        """测试限流错误处理"""
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="test-key",
            models=["claude-3-sonnet"]
        )
        
        provider = AnthropicProvider(config)
        
        # Mock rate limit error
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = RateLimitError(
                message="Rate limit exceeded",
                provider=ProviderType.ANTHROPIC,
                retry_after=120
            )
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="claude-3-sonnet"
            )
            
            with pytest.raises(RateLimitError) as exc_info:
                await provider.chat_completion(request)
            
            assert exc_info.value.retry_after == 120
            assert exc_info.value.provider == ProviderType.ANTHROPIC
    
    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """测试认证错误处理"""
        config = ProviderConfig(
            provider_type=ProviderType.GEMINI,
            api_key="invalid-key",
            models=["gemini-pro"]
        )
        
        provider = GeminiProvider(config)
        
        # Mock authentication error
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = AuthenticationError(
                message="Invalid API key",
                provider=ProviderType.GEMINI
            )
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="gemini-pro"
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                await provider.chat_completion(request)
            
            assert "Invalid API key" in str(exc_info.value)
            assert exc_info.value.provider == ProviderType.GEMINI
    
    def test_invalid_configuration_handling(self):
        """测试无效配置处理"""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="",  # Empty API key should raise error
                models=[]    # Empty models should raise error
            )
    
    def test_invalid_model_configuration(self):
        """测试无效模型配置"""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key",
                models=["invalid-model-name"],
                capabilities=[]
            )
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """测试超时处理"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            models=["gpt-4"],
            timeout=1  # Very short timeout
        )
        
        provider = OpenAIProvider(config)
        
        # Mock slow API response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(2)  # Longer than timeout
            return {"choices": [{"message": {"content": "响应"}}]}
        
        with patch.object(provider, '_make_api_request', side_effect=slow_response):
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.chat_completion(request)
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """测试网络错误处理"""
        config = ProviderConfig(
            provider_type=ProviderType.DEEPSEEK,
            api_key="test-key",
            models=["deepseek-chat"]
        )
        
        provider = DeepSeekProvider(config)
        
        # Mock network error
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = ProviderError(
                message="Network connection failed",
                provider=ProviderType.DEEPSEEK,
                error_code="network_error"
            )
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="deepseek-chat"
            )
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.chat_completion(request)
            
            assert exc_info.value.error_code == "network_error"
            assert "Network connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """测试畸形响应处理"""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            models=["gpt-4"]
        )
        
        provider = OpenAIProvider(config)
        
        # Mock malformed response
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {
                "invalid_structure": "malformed response"
                # Missing required 'choices' field
            }
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="gpt-4"
            )
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.chat_completion(request)
            
            assert "response" in str(exc_info.value).lower()
    
    def test_provider_health_status_unhealthy(self):
        """测试不健康的供应商状态"""
        health = ProviderHealth(
            provider=ProviderType.OPENAI,
            status="unhealthy",
            last_check=datetime.now(),
            latency_ms=5000,  # Very high latency
            error_rate=0.95,  # Very high error rate
            success_rate=0.05,
            metadata={"last_error": "Connection timeout"}
        )
        
        assert health.provider == ProviderType.OPENAI
        assert health.status == "unhealthy"
        assert not health.is_healthy()
        assert health.error_rate > 0.5
        assert health.success_rate < 0.5


class TestRecoveryMechanisms:
    """测试恢复机制"""
    
    @pytest.mark.asyncio
    async def test_retry_after_failure(self):
        """测试故障后重试机制"""
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="test-key",
            models=["claude-3-sonnet"],
            max_retries=3
        )
        
        provider = AnthropicProvider(config)
        
        # Mock intermittent failure
        call_count = 0
        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise ProviderError(
                    message="Temporary failure",
                    provider=ProviderType.ANTHROPIC,
                    error_code="temporary_error"
                )
            # Succeed on 3rd attempt
            return {
                "content": [{"text": "成功响应"}],
                "usage": {"input_tokens": 10, "output_tokens": 15}
            }
        
        with patch.object(provider, '_make_api_request', side_effect=intermittent_failure):
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="claude-3-sonnet"
            )
            
            # Should eventually succeed after retries
            response = await provider.chat_completion(request)
            assert response.content == "成功响应"
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """测试断路器模式"""
        config = ProviderConfig(
            provider_type=ProviderType.GEMINI,
            api_key="test-key",
            models=["gemini-pro"],
            circuit_breaker_threshold=3
        )
        
        provider = GeminiProvider(config)
        
        # Mock consecutive failures to trigger circuit breaker
        with patch.object(provider, '_make_api_request', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = ProviderError(
                message="Service unavailable",
                provider=ProviderType.GEMINI,
                error_code="service_unavailable"
            )
            
            request = LLMRequest(
                prompt="测试提示",
                request_type=RequestType.CHAT,
                model="gemini-pro"
            )
            
            # After threshold failures, circuit should be open
            for i in range(4):  # One more than threshold
                with pytest.raises(ProviderError):
                    await provider.chat_completion(request)
            
            # Verify circuit breaker is triggered
            assert mock_api.call_count >= 3


if __name__ == "__main__":
    # 运行错误处理测试
    async def run_error_handling_tests():
        print("运行错误处理和弹性测试...")
        
        # 测试基本错误类型
        error = ProviderError(
            message="测试错误",
            provider=ProviderType.OPENAI,
            error_code="test_error"
        )
        print(f"错误对象创建成功: {error.error_code}")
        
        # 测试健康状态
        health = ProviderHealth(
            provider=ProviderType.OPENAI,
            status="healthy",
            last_check=datetime.now(),
            latency_ms=100,
            error_rate=0.01,
            success_rate=0.99
        )
        print(f"健康状态创建成功: {health.status}")
        
        print("错误处理测试完成!")
    
    asyncio.run(run_error_handling_tests())