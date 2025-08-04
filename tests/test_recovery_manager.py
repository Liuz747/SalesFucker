"""
恢复管理器(Recovery Manager)组件测试套件

该测试模块专注于恢复管理器的核心功能测试:
- 恢复策略选择(立即故障转移、重试退避、断路器)
- 恢复动作执行
- 恢复历史跟踪
- 自适应恢复优化
- 退避延迟计算
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.failover_system.recovery_manager import RecoveryManager, RecoveryStrategy
from src.llm.failover_system.failure_detector import FailurePattern
from src.llm.failover_system.models import (
    FailureType, RecoveryAction, ProviderStatus
)
from src.llm.provider_config import ProviderType
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType, 
    ProviderError
)


class TestRecoveryManager:
    """测试恢复管理器组件"""
    
    @pytest.fixture
    def recovery_manager(self):
        """恢复管理器fixture"""
        return RecoveryManager()
    
    def test_recovery_strategy_selection(self, recovery_manager):
        """测试恢复策略选择"""
        # Test immediate failover for critical errors
        critical_error = ProviderError(
            message="Service completely unavailable",
            provider=ProviderType.OPENAI,
            error_code="service_unavailable",
            retry_after=None
        )
        
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.OPENAI,
            error=critical_error,
            failure_pattern=FailurePattern(
                failure_type=FailureType.SERVICE_UNAVAILABLE,
                severity=0.9,
                consecutive_count=5
            )
        )
        
        assert strategy == RecoveryStrategy.IMMEDIATE_FAILOVER
    
    def test_retry_with_backoff_strategy(self, recovery_manager):
        """测试退避重试策略"""
        # Test retry for transient errors
        transient_error = ProviderError(
            message="Temporary rate limit",
            provider=ProviderType.ANTHROPIC,
            error_code="rate_limit_exceeded",
            retry_after=60
        )
        
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.ANTHROPIC,
            error=transient_error,
            failure_pattern=FailurePattern(
                failure_type=FailureType.RATE_LIMIT,
                severity=0.3,
                consecutive_count=1
            )
        )
        
        assert strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        
        # Calculate backoff delay
        backoff_delay = recovery_manager.calculate_backoff_delay(
            attempt=3,
            base_delay=1.0,
            max_delay=30.0
        )
        
        # Should be exponential backoff
        assert backoff_delay > 1.0
        assert backoff_delay <= 30.0
    
    def test_circuit_breaker_strategy(self, recovery_manager):
        """测试断路器策略"""
        # Test circuit breaker for repeated failures
        repeated_error = ProviderError(
            message="Multiple timeouts",
            provider=ProviderType.GEMINI,
            error_code="timeout",
            retry_after=None
        )
        
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.GEMINI,
            error=repeated_error,
            failure_pattern=FailurePattern(
                failure_type=FailureType.TIMEOUT,
                severity=0.7,
                consecutive_count=4
            )
        )
        
        assert strategy == RecoveryStrategy.CIRCUIT_BREAKER
    
    @pytest.mark.asyncio
    async def test_recovery_action_execution(self, recovery_manager):
        """测试恢复动作执行"""
        # Mock provider manager
        mock_provider_manager = Mock()
        mock_fallback_provider = Mock()
        mock_fallback_provider.chat_completion = AsyncMock(return_value=LLMResponse(
            content="恢复响应",
            model="fallback-model",
            provider=ProviderType.ANTHROPIC,
            cost=0.001,
            input_tokens=10,
            output_tokens=5,
            latency_ms=500
        ))
        
        mock_provider_manager.get_provider.return_value = mock_fallback_provider
        
        # Create recovery action
        action = RecoveryAction(
            strategy=RecoveryStrategy.IMMEDIATE_FAILOVER,
            target_provider=ProviderType.ANTHROPIC,
            original_request=LLMRequest(
                prompt="测试恢复请求",
                request_type=RequestType.CHAT,
                model="gpt-4"
            ),
            context_data={"conversation_id": "conv_recovery"}
        )
        
        # Execute recovery
        result = await recovery_manager.execute_recovery_action(
            action=action,
            provider_manager=mock_provider_manager
        )
        
        assert result.success is True
        assert result.response.content == "恢复响应"
        assert result.response.provider == ProviderType.ANTHROPIC
        assert result.recovery_latency_ms > 0
    
    def test_recovery_history_tracking(self, recovery_manager):
        """测试恢复历史跟踪"""
        provider = ProviderType.OPENAI
        
        # Record recovery attempts
        recovery_manager.record_recovery_attempt(
            provider=provider,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            success=False,
            latency_ms=2000
        )
        
        recovery_manager.record_recovery_attempt(
            provider=provider,
            strategy=RecoveryStrategy.IMMEDIATE_FAILOVER,
            success=True,
            latency_ms=1000
        )
        
        # Get recovery history
        history = recovery_manager.get_recovery_history(provider)
        
        assert len(history) == 2
        assert history[0].success is False
        assert history[1].success is True
        assert history[1].strategy == RecoveryStrategy.IMMEDIATE_FAILOVER
    
    def test_adaptive_recovery_optimization(self, recovery_manager):
        """测试自适应恢复优化"""
        provider = ProviderType.DEEPSEEK
        
        # Record multiple recovery attempts
        for i in range(10):
            success = i >= 7  # Last 3 attempts successful
            strategy = RecoveryStrategy.IMMEDIATE_FAILOVER if success else RecoveryStrategy.RETRY_WITH_BACKOFF
            
            recovery_manager.record_recovery_attempt(
                provider=provider,
                strategy=strategy,
                success=success,
                latency_ms=1000 if success else 3000
            )
        
        # Get optimized strategy recommendation
        optimized_strategy = recovery_manager.get_optimized_strategy(provider)
        
        # Should recommend immediate failover based on success pattern
        assert optimized_strategy == RecoveryStrategy.IMMEDIATE_FAILOVER


if __name__ == "__main__":
    # 运行恢复管理器测试
    def run_recovery_manager_tests():
        print("运行恢复管理器测试...")
        
        # 测试恢复管理器初始化
        recovery_manager = RecoveryManager()
        print("恢复管理器初始化成功")
        
        # 测试策略选择
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.OPENAI,
            error=ProviderError("Test", ProviderType.OPENAI, "test"),
            failure_pattern=FailurePattern(FailureType.TIMEOUT, 0.5, 1)
        )
        print(f"恢复策略选择成功: {strategy}")
        
        # 测试退避延迟计算
        delay = recovery_manager.calculate_backoff_delay(
            attempt=2,
            base_delay=1.0,
            max_delay=10.0
        )
        print(f"退避延迟计算成功: {delay}秒")
        
        print("恢复管理器测试完成!")
    
    run_recovery_manager_tests()