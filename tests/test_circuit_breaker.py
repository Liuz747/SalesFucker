"""
断路器(Circuit Breaker)组件测试套件

该测试模块专注于断路器模式的核心功能测试:
- 断路器状态转换(CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- 故障计数和阈值管理
- 超时和恢复机制
- 异步操作支持
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from src.llm.failover_system.circuit_breaker import CircuitBreaker, CircuitState
from src.llm.provider_config import ProviderType


class TestCircuitBreaker:
    """测试断路器组件功能"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """断路器fixture"""
        return CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=60,
            recovery_timeout=30
        )
    
    def test_circuit_breaker_initialization(self, circuit_breaker):
        """测试断路器初始化"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time is None
        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.timeout_seconds == 60
    
    def test_circuit_breaker_failure_counting(self, circuit_breaker):
        """测试断路器故障计数"""
        # Record failures
        circuit_breaker.record_failure(ProviderType.OPENAI, "API timeout")
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == CircuitState.CLOSED
        
        circuit_breaker.record_failure(ProviderType.OPENAI, "Rate limit exceeded")
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # Third failure should open circuit
        circuit_breaker.record_failure(ProviderType.OPENAI, "Service unavailable")
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.last_failure_time is not None
    
    def test_circuit_breaker_open_state_behavior(self, circuit_breaker):
        """测试断路器开启状态行为"""
        # Force circuit to open
        for _ in range(3):
            circuit_breaker.record_failure(ProviderType.OPENAI, "Test failure")
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Should reject requests in open state
        with pytest.raises(Exception) as exc_info:
            circuit_breaker.call(lambda: "should not execute")
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    def test_circuit_breaker_half_open_transition(self, circuit_breaker):
        """测试断路器半开状态转换"""
        # Force circuit to open
        for _ in range(3):
            circuit_breaker.record_failure(ProviderType.OPENAI, "Test failure")
        
        # Mock time passage
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=65)
        
        # Check if should transition to half-open
        assert circuit_breaker._should_attempt_reset()
        
        # Attempt reset
        circuit_breaker._attempt_reset()
        assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_successful_recovery(self, circuit_breaker):
        """测试断路器成功恢复"""
        # Force to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.failure_count = 3
        
        # Record successful call
        result = circuit_breaker.call(lambda: "success")
        
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
    
    def test_circuit_breaker_failed_recovery(self, circuit_breaker):
        """测试断路器恢复失败"""
        # Force to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.failure_count = 2
        
        # Record failed call
        with pytest.raises(Exception):
            circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Recovery failed")))
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async_operations(self, circuit_breaker):
        """测试断路器异步操作"""
        async def async_success():
            await asyncio.sleep(0.1)
            return "async success"
        
        async def async_failure():
            await asyncio.sleep(0.1)
            raise Exception("async failure")
        
        # Test successful async call
        result = await circuit_breaker.call_async(async_success)
        assert result == "async success"
        assert circuit_breaker.failure_count == 0
        
        # Test failed async call
        with pytest.raises(Exception):
            await circuit_breaker.call_async(async_failure)
        
        assert circuit_breaker.failure_count == 1


if __name__ == "__main__":
    # 运行断路器测试
    def run_circuit_breaker_tests():
        print("运行断路器测试...")
        
        # 测试断路器初始化
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        assert circuit_breaker.state == CircuitState.CLOSED
        print(f"断路器初始化成功: {circuit_breaker.state}")
        
        # 测试故障记录
        circuit_breaker.record_failure(ProviderType.OPENAI, "Test failure")
        assert circuit_breaker.failure_count == 1
        print(f"故障记录成功: {circuit_breaker.failure_count}")
        
        print("断路器测试完成!")
    
    run_circuit_breaker_tests()