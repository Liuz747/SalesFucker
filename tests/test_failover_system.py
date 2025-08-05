"""
多LLM系统简化重试逻辑测试

该测试文件替代了原有的复杂故障转移系统测试，专注于测试新的简化重试逻辑。
原有的故障转移系统已被移除，替换为更简单、更可靠的重试机制。

测试覆盖:
- MultiLLMClient的重试逻辑
- 供应商故障处理
- 简化的错误恢复
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List

from src.llm.multi_llm_client import MultiLLMClient
from src.llm.provider_config import ProviderType, GlobalProviderConfig, ProviderConfig, ProviderCredentials
from src.llm.base_provider import ProviderError, RateLimitError
from src.llm.intelligent_router import RoutingStrategy


class TestMultiLLMRetryLogic:
    """测试多LLM客户端的重试逻辑"""
    
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
                ),
                "anthropic": ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.ANTHROPIC,
                        api_key="test-key"
                    ),
                    is_enabled=True
                )
            }
        )
    
    @pytest.fixture
    async def multi_llm_client(self, mock_config):
        """创建多LLM客户端"""
        with patch('src.llm.multi_llm_client.ProviderManager') as mock_pm, \
             patch('src.llm.multi_llm_client.IntelligentRouter') as mock_router, \
             patch('src.llm.multi_llm_client.CostOptimizer') as mock_co:
            
            client = MultiLLMClient(mock_config)
            yield client
    
    @pytest.mark.asyncio
    async def test_retry_on_provider_failure(self, multi_llm_client):
        """测试供应商失败时的重试逻辑"""
        # 模拟第一次失败，第二次成功
        mock_provider1 = Mock()
        mock_provider1.provider_type = ProviderType.OPENAI
        mock_provider1.chat_completion = AsyncMock(side_effect=ProviderError("Test error", ProviderType.OPENAI, "TEST_ERR"))
        
        mock_provider2 = Mock()
        mock_provider2.provider_type = ProviderType.ANTHROPIC
        mock_provider2.chat_completion = AsyncMock(return_value=Mock(content="Success", cost=0.01))
        
        multi_llm_client.router.route_request = AsyncMock(side_effect=[mock_provider1, mock_provider2])
        
        messages = [{"role": "user", "content": "Test message"}]
        
        result = await multi_llm_client.chat_completion(
            messages=messages,
            agent_type="test",
            max_retries=2
        )
        
        assert result.content == "Success"
        assert multi_llm_client.router.route_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, multi_llm_client):
        """测试达到最大重试次数"""
        mock_provider = Mock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.chat_completion = AsyncMock(side_effect=ProviderError("Persistent error", ProviderType.OPENAI, "PERSISTENT_ERR"))
        
        multi_llm_client.router.route_request = AsyncMock(return_value=mock_provider)
        
        messages = [{"role": "user", "content": "Test message"}]
        
        with pytest.raises(ProviderError, match="Persistent error"):
            await multi_llm_client.chat_completion(
                messages=messages,
                agent_type="test",
                max_retries=2
            )
        
        # 应该尝试3次(初始+2次重试)
        assert mock_provider.chat_completion.call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_rate_limit(self, multi_llm_client):
        """测试速率限制错误不进行重试"""
        mock_provider = Mock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.chat_completion = AsyncMock(side_effect=RateLimitError("Rate limited", ProviderType.OPENAI, "RATE_LIMIT"))
        
        multi_llm_client.router.route_request = AsyncMock(return_value=mock_provider)
        
        messages = [{"role": "user", "content": "Test message"}]
        
        with pytest.raises(RateLimitError, match="Rate limited"):
            await multi_llm_client.chat_completion(
                messages=messages,
                agent_type="test",
                max_retries=2
            )
        
        # 速率限制错误不应该重试
        assert mock_provider.chat_completion.call_count == 1
    
    @pytest.mark.asyncio
    async def test_success_on_first_try(self, multi_llm_client):
        """测试第一次尝试就成功"""
        mock_provider = Mock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.chat_completion = AsyncMock(return_value=Mock(content="Success", cost=0.01))
        
        multi_llm_client.router.route_request = AsyncMock(return_value=mock_provider)
        
        messages = [{"role": "user", "content": "Test message"}]
        
        result = await multi_llm_client.chat_completion(
            messages=messages,
            agent_type="test",
            max_retries=2
        )
        
        assert result.content == "Success"
        # 成功时只调用一次
        assert mock_provider.chat_completion.call_count == 1
        assert multi_llm_client.router.route_request.call_count == 1


class TestProviderHealthHandling:
    """测试供应商健康状态处理"""
    
    @pytest.mark.asyncio
    async def test_unhealthy_provider_exclusion(self):
        """测试不健康的供应商被排除"""
        # 这个测试应该集成到实际的路由器测试中
        # 因为健康检查逻辑现在在路由器中处理
        pass
    
    @pytest.mark.asyncio
    async def test_provider_recovery_detection(self):
        """测试供应商恢复检测"""
        # 这个测试应该集成到供应商管理器测试中
        # 因为恢复检测现在通过健康检查实现
        pass


class TestLegacyFailoverSystemRemoval:
    """确认旧的故障转移系统已被移除"""
    
    def test_failover_system_imports_removed(self):
        """确认故障转移系统导入已移除"""
        try:
            from src.llm.failover_system import FailoverSystem
            pytest.fail("FailoverSystem should have been removed")
        except ImportError:
            pass  # 预期的行为
    
    def test_circuit_breaker_imports_removed(self):
        """确认断路器导入已移除"""
        try:
            from src.llm.failover_system.circuit_breaker import CircuitBreaker
            pytest.fail("CircuitBreaker should have been removed")
        except ImportError:
            pass  # 预期的行为
    
    def test_recovery_manager_imports_removed(self):
        """确认恢复管理器导入已移除"""
        try:
            from src.llm.failover_system.recovery_manager import RecoveryManager
            pytest.fail("RecoveryManager should have been removed")
        except ImportError:
            pass  # 预期的行为


if __name__ == "__main__":
    pytest.main([__file__])