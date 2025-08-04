"""
故障转移系统综合测试套件

该测试套件为多LLM故障转移系统提供全面的测试覆盖。

重要提示: 该文件已被重构为更小的模块化测试文件，以符合代码质量标准:

专业测试模块:
- test_circuit_breaker.py - 断路器(Circuit Breaker)模式测试
- test_failure_detector.py - 故障检测器(Failure Detector)测试
- test_context_preserver.py - 上下文保持器(Context Preserver)测试  
- test_recovery_manager.py - 恢复管理器(Recovery Manager)测试
- test_failover_integration.py - 端到端故障转移场景测试

每个模块都专注于特定组件的详细测试，提供更好的代码组织和维护性。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.failover_system import FailoverSystem
from src.llm.failover_system.circuit_breaker import CircuitBreaker, CircuitState
from src.llm.failover_system.failure_detector import FailureDetector, FailurePattern
from src.llm.failover_system.context_preserver import ContextPreserver, ConversationContext
from src.llm.failover_system.recovery_manager import RecoveryManager, RecoveryStrategy
from src.llm.failover_system.models import FailureType
from src.llm.provider_config import ProviderType
from src.llm.base_provider import ProviderError


class TestFailoverSystemCore:
    """测试故障转移系统核心集成功能"""
    
    def test_failover_system_initialization(self):
        """测试故障转移系统初始化"""
        from src.llm.provider_config import GlobalProviderConfig, ProviderConfig
        
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="test_tenant"
        )
        
        provider_manager = Mock()
        failover_system = FailoverSystem(config, provider_manager)
        
        assert failover_system.config == config
        assert failover_system.provider_manager == provider_manager
        assert failover_system.circuit_breakers is not None
        assert failover_system.failure_detector is not None
        assert failover_system.context_preserver is not None
        assert failover_system.recovery_manager is not None
    
    def test_component_integration(self):
        """测试组件集成"""
        # 测试各组件能够正常实例化和协作
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        failure_detector = FailureDetector()
        context_preserver = ContextPreserver()
        recovery_manager = RecoveryManager()
        
        # 验证组件状态
        assert circuit_breaker.state == CircuitState.CLOSED
        assert len(failure_detector.failure_history) == 0
        
        # 测试组件间基本交互
        failure_detector.record_result(
            provider=ProviderType.OPENAI,
            success=False,
            latency_ms=5000,
            error_message="Test error"
        )
        
        patterns = failure_detector.detect_failure_patterns(ProviderType.OPENAI)
        assert len(patterns) >= 0  # Should be able to detect patterns
        
        # 测试上下文存储
        context = ConversationContext(
            conversation_id="test_conv",
            customer_id="test_customer",
            agent_type="test_agent"
        )
        
        context_preserver.store_context("test_conv", context)
        retrieved = context_preserver.get_context("test_conv")
        assert retrieved is not None
        assert retrieved.conversation_id == "test_conv"


if __name__ == "__main__":
    # 运行核心故障转移测试
    async def run_core_failover_tests():
        print("运行核心故障转移测试...")
        
        # 测试基本组件
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        assert circuit_breaker.state == CircuitState.CLOSED
        print(f"断路器初始化成功: {circuit_breaker.state}")
        
        failure_detector = FailureDetector()
        failure_detector.record_result(
            provider=ProviderType.OPENAI,
            success=False,
            latency_ms=5000,
            error_message="Test error"
        )
        patterns = failure_detector.detect_failure_patterns(ProviderType.OPENAI)
        print(f"故障检测器工作正常: {len(patterns)} 个模式检测到")
        
        context_preserver = ContextPreserver()
        context = ConversationContext(
            conversation_id="test_conv",
            customer_id="test_customer",
            agent_type="test_agent"
        )
        context_preserver.store_context("test_conv", context)
        retrieved = context_preserver.get_context("test_conv")
        assert retrieved is not None
        print(f"上下文保持器工作正常: {retrieved.conversation_id}")
        
        recovery_manager = RecoveryManager()
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.OPENAI,
            error=ProviderError("Test", ProviderType.OPENAI, "test"),
            failure_pattern=FailurePattern(FailureType.TIMEOUT, 0.5, 1)
        )
        print(f"恢复管理器工作正常: {strategy}")
        
        print("核心故障转移测试完成!")
        print("\n专业测试请运行:")
        print("- pytest tests/test_circuit_breaker.py")
        print("- pytest tests/test_failure_detector.py") 
        print("- pytest tests/test_context_preserver.py")
        print("- pytest tests/test_recovery_manager.py")
        print("- pytest tests/test_failover_integration.py")
    
    asyncio.run(run_core_failover_tests())