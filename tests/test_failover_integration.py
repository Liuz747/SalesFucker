"""
故障转移系统集成测试套件

该测试模块专注于故障转移系统的端到端集成测试:
- 级联故障场景测试
- 上下文保持期间故障转移
- 断路器集成测试
- 性能影响监控
- 完整故障转移工作流
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.failover_system import FailoverSystem
from src.llm.failover_system.circuit_breaker import CircuitBreaker, CircuitState
from src.llm.failover_system.context_preserver import ConversationContext
from src.llm.failover_system.recovery_manager import RecoveryStrategy
from src.llm.failover_system.models import FailureType
from src.llm.provider_config import ProviderType, GlobalProviderConfig, ProviderConfig
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType, 
    ProviderError
)
from src.llm.provider_manager import ProviderManager


class TestIntegratedFailoverScenarios:
    """测试集成故障转移场景"""
    
    @pytest.fixture
    def full_failover_system(self):
        """完整故障转移系统fixture"""
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
            tenant_id="failover_test"
        )
        
        provider_manager = Mock(spec=ProviderManager)
        failover_system = FailoverSystem(config, provider_manager)
        
        return failover_system, provider_manager
    
    @pytest.mark.asyncio
    async def test_cascading_failure_scenario(self, full_failover_system):
        """测试级联故障场景"""
        failover_system, provider_manager = full_failover_system
        
        # Mock primary provider failure
        primary_provider = Mock()
        primary_provider.chat_completion = AsyncMock(side_effect=ProviderError(
            message="Primary service down",
            provider=ProviderType.OPENAI,
            error_code="service_unavailable"
        ))
        
        # Mock secondary provider success
        secondary_provider = Mock()
        secondary_provider.chat_completion = AsyncMock(return_value=LLMResponse(
            content="故障转移成功响应",
            model="claude-3-sonnet",
            provider=ProviderType.ANTHROPIC,
            cost=0.002,
            input_tokens=15,
            output_tokens=20,
            latency_ms=800
        ))
        
        # Setup provider manager mocks
        def get_provider_side_effect(provider_type):
            if provider_type == ProviderType.OPENAI:
                return primary_provider
            elif provider_type == ProviderType.ANTHROPIC:
                return secondary_provider
            return Mock()
        
        provider_manager.get_provider.side_effect = get_provider_side_effect
        provider_manager.get_available_providers.return_value = [
            ProviderType.ANTHROPIC, ProviderType.GEMINI
        ]
        
        # Create request
        request = LLMRequest(
            prompt="需要故障转移的请求",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        # Execute with failover
        result = await failover_system.execute_with_failover(
            request=request,
            primary_provider=ProviderType.OPENAI,
            fallback_providers=[ProviderType.ANTHROPIC, ProviderType.GEMINI],
            conversation_id="conv_cascade_test"
        )
        
        assert result.success is True
        assert result.response.content == "故障转移成功响应"
        assert result.response.provider == ProviderType.ANTHROPIC
        assert result.failover_occurred is True
        assert result.original_provider == ProviderType.OPENAI
        assert result.recovery_strategy == RecoveryStrategy.IMMEDIATE_FAILOVER
    
    @pytest.mark.asyncio
    async def test_context_preservation_during_failover(self, full_failover_system):
        """测试故障转移期间上下文保持"""
        failover_system, provider_manager = full_failover_system
        
        conversation_id = "conv_context_test"
        
        # Setup conversation context
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_context",
            agent_type="sales",
            conversation_history=[
                {"role": "user", "content": "我想要抗衰老产品"},
                {"role": "assistant", "content": "我来为您推荐合适的产品"}
            ],
            customer_profile={
                "age_range": "40-50",
                "skin_type": "dry",
                "budget": "premium"
            },
            current_state="product_recommendation"
        )
        
        failover_system.context_preserver.store_context(conversation_id, context)
        
        # Mock provider failure and recovery
        failed_provider = Mock()
        failed_provider.chat_completion = AsyncMock(side_effect=ProviderError(
            message="Connection timeout",
            provider=ProviderType.OPENAI,
            error_code="timeout"
        ))
        
        recovery_provider = Mock()
        recovery_provider.chat_completion = AsyncMock(return_value=LLMResponse(
            content="基于您的干性肌肤和抗衰老需求，我推荐...",
            model="claude-3-sonnet",
            provider=ProviderType.ANTHROPIC,
            cost=0.003,
            input_tokens=25,
            output_tokens=30,
            latency_ms=900
        ))
        
        provider_manager.get_provider.side_effect = lambda p: (
            failed_provider if p == ProviderType.OPENAI else recovery_provider
        )
        
        # Execute with context preservation
        request = LLMRequest(
            prompt="请根据我的需求推荐产品",
            request_type=RequestType.CHAT,
            model="auto",
            metadata={"conversation_id": conversation_id}
        )
        
        result = await failover_system.execute_with_failover(
            request=request,
            primary_provider=ProviderType.OPENAI,
            fallback_providers=[ProviderType.ANTHROPIC],
            conversation_id=conversation_id
        )
        
        # Verify context was preserved and transferred
        preserved_context = failover_system.context_preserver.get_context(conversation_id)
        assert preserved_context is not None
        assert preserved_context.current_provider == ProviderType.ANTHROPIC
        assert preserved_context.customer_profile["skin_type"] == "dry"
        assert "抗衰老" in preserved_context.conversation_history[0]["content"]
        
        assert result.success is True
        assert "抗衰老需求" in result.response.content
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, full_failover_system):
        """测试断路器集成"""
        failover_system, provider_manager = full_failover_system
        
        provider = ProviderType.GEMINI
        
        # Setup failing provider
        failing_provider = Mock()
        failing_provider.chat_completion = AsyncMock(side_effect=ProviderError(
            message="Service overloaded",
            provider=provider,
            error_code="service_overloaded"
        ))
        
        provider_manager.get_provider.return_value = failing_provider
        
        request = LLMRequest(
            prompt="测试断路器",
            request_type=RequestType.CHAT,
            model="gemini-pro"
        )
        
        # Make multiple failing requests to trigger circuit breaker
        for i in range(5):
            try:
                await failover_system.execute_with_failover(
                    request=request,
                    primary_provider=provider,
                    fallback_providers=[],
                    conversation_id=f"conv_cb_test_{i}"
                )
            except Exception:
                pass  # Expected failures
        
        # Circuit should now be open
        circuit_breaker = failover_system.circuit_breakers.get(provider)
        assert circuit_breaker is not None
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Next request should be rejected immediately
        with pytest.raises(Exception) as exc_info:
            await failover_system.execute_with_failover(
                request=request,
                primary_provider=provider,
                fallback_providers=[],
                conversation_id="conv_cb_rejected"
            )
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    def test_performance_impact_monitoring(self, full_failover_system):
        """测试性能影响监控"""
        failover_system, provider_manager = full_failover_system
        
        # Record failover events
        for i in range(10):
            failover_system.record_failover_event(
                original_provider=ProviderType.OPENAI,
                fallback_provider=ProviderType.ANTHROPIC,
                success=i >= 7,  # 70% success rate
                latency_ms=1200 + (i * 100),
                error_type=FailureType.TIMEOUT if i < 7 else None
            )
        
        # Get performance metrics
        metrics = failover_system.get_failover_metrics(ProviderType.OPENAI)
        
        assert metrics["total_failovers"] == 10
        assert metrics["success_rate"] == 0.3  # 3 out of 10 successful
        assert metrics["avg_latency_ms"] > 1200
        assert metrics["most_common_error"] == FailureType.TIMEOUT


if __name__ == "__main__":
    # 运行集成故障转移测试
    async def run_integration_failover_tests():
        print("运行集成故障转移测试...")
        
        # 测试基本组件
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        assert circuit_breaker.state == CircuitState.CLOSED
        print(f"断路器状态验证: {circuit_breaker.state}")
        
        # 测试上下文
        context = ConversationContext(
            conversation_id="test_conv",
            customer_id="test_customer",
            agent_type="test_agent"
        )
        print(f"上下文创建成功: {context.conversation_id}")
        
        print("集成故障转移测试完成!")
    
    asyncio.run(run_integration_failover_tests())