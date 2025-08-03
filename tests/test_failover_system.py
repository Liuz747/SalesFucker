"""
故障转移系统综合测试套件

该测试套件为多LLM故障转移系统提供全面的测试覆盖，包括:
- 断路器(Circuit Breaker)模式测试
- 故障检测器(Failure Detector)测试  
- 上下文保持器(Context Preserver)测试
- 恢复管理器(Recovery Manager)测试
- 端到端故障转移场景测试
- 多层级故障处理测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from src.llm.failover_system import FailoverSystem
from src.llm.failover_system.circuit_breaker import CircuitBreaker, CircuitState
from src.llm.failover_system.failure_detector import FailureDetector, FailurePattern
from src.llm.failover_system.context_preserver import ContextPreserver, ConversationContext
from src.llm.failover_system.recovery_manager import RecoveryManager, RecoveryStrategy
from src.llm.failover_system.models import (
    FailureType, FailureRecord, FailoverDecision, 
    RecoveryAction, ProviderStatus
)
from src.llm.provider_config import ProviderType, GlobalProviderConfig, ProviderConfig
from src.llm.base_provider import (
    LLMRequest, LLMResponse, RequestType, 
    ProviderError, ProviderHealth
)
from src.llm.provider_manager import ProviderManager


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


class TestFailureDetector:
    """测试故障检测器组件"""
    
    @pytest.fixture
    def failure_detector(self):
        """故障检测器fixture"""
        return FailureDetector(
            error_rate_threshold=0.5,
            latency_threshold=5000,
            consecutive_failures_threshold=3
        )
    
    def test_failure_detector_initialization(self, failure_detector):
        """测试故障检测器初始化"""
        assert failure_detector.error_rate_threshold == 0.5
        assert failure_detector.latency_threshold == 5000
        assert failure_detector.consecutive_failures_threshold == 3
        assert len(failure_detector.failure_history) == 0
    
    def test_error_rate_detection(self, failure_detector):
        """测试错误率检测"""
        provider = ProviderType.OPENAI
        
        # Record mixed success/failure pattern (60% failure rate)
        for i in range(10):
            success = i < 4  # 4 successes, 6 failures
            failure_detector.record_result(
                provider=provider,
                success=success,
                latency_ms=1000,
                error_message="Test error" if not success else None
            )
        
        # Check if failure pattern detected
        patterns = failure_detector.detect_failure_patterns(provider)
        
        high_error_patterns = [p for p in patterns if p.failure_type == FailureType.HIGH_ERROR_RATE]
        assert len(high_error_patterns) > 0
        assert high_error_patterns[0].severity > 0.5
    
    def test_latency_spike_detection(self, failure_detector):
        """测试延迟峰值检测"""
        provider = ProviderType.ANTHROPIC
        
        # Record high latency results
        for _ in range(5):
            failure_detector.record_result(
                provider=provider,
                success=True,
                latency_ms=6000,  # Above threshold
                error_message=None
            )
        
        patterns = failure_detector.detect_failure_patterns(provider)
        
        latency_patterns = [p for p in patterns if p.failure_type == FailureType.LATENCY_SPIKE]
        assert len(latency_patterns) > 0
        assert latency_patterns[0].avg_latency > failure_detector.latency_threshold
    
    def test_consecutive_failures_detection(self, failure_detector):
        """测试连续故障检测"""
        provider = ProviderType.GEMINI
        
        # Record consecutive failures
        for i in range(5):
            failure_detector.record_result(
                provider=provider,
                success=False,
                latency_ms=1000,
                error_message=f"Consecutive error {i+1}"
            )
        
        patterns = failure_detector.detect_failure_patterns(provider)
        
        consecutive_patterns = [p for p in patterns if p.failure_type == FailureType.CONSECUTIVE_FAILURES]
        assert len(consecutive_patterns) > 0
        assert consecutive_patterns[0].consecutive_count >= failure_detector.consecutive_failures_threshold
    
    def test_timeout_detection(self, failure_detector):
        """测试超时检测"""
        provider = ProviderType.DEEPSEEK
        
        # Record timeout errors
        for _ in range(3):
            failure_detector.record_result(
                provider=provider,
                success=False,
                latency_ms=10000,  # Very high latency
                error_message="Request timeout"
            )
        
        patterns = failure_detector.detect_failure_patterns(provider)
        
        timeout_patterns = [p for p in patterns if p.failure_type == FailureType.TIMEOUT]
        assert len(timeout_patterns) > 0
    
    def test_pattern_severity_calculation(self, failure_detector):
        """测试模式严重程度计算"""
        provider = ProviderType.OPENAI
        
        # Record severe failure pattern
        for _ in range(10):
            failure_detector.record_result(
                provider=provider,
                success=False,
                latency_ms=8000,
                error_message="Critical system error"
            )
        
        patterns = failure_detector.detect_failure_patterns(provider)
        
        # Should detect high severity
        assert any(p.severity > 0.8 for p in patterns)
    
    def test_time_window_filtering(self, failure_detector):
        """测试时间窗口过滤"""
        provider = ProviderType.ANTHROPIC
        
        # Record old failures (should be ignored)
        old_time = datetime.now() - timedelta(hours=2)
        failure_detector.failure_history[provider] = [
            FailureRecord(
                timestamp=old_time,
                provider=provider,
                success=False,
                latency_ms=1000,
                error_message="Old error"
            )
        ]
        
        # Record recent failures
        for _ in range(2):
            failure_detector.record_result(
                provider=provider,
                success=False,
                latency_ms=1000,
                error_message="Recent error"
            )
        
        # Detect patterns with time window
        patterns = failure_detector.detect_failure_patterns(
            provider=provider,
            time_window=timedelta(minutes=30)
        )
        
        # Should only consider recent failures
        consecutive_patterns = [p for p in patterns if p.failure_type == FailureType.CONSECUTIVE_FAILURES]
        if consecutive_patterns:
            assert consecutive_patterns[0].consecutive_count == 2  # Only recent failures


class TestContextPreserver:
    """测试上下文保持器组件"""
    
    @pytest.fixture
    def context_preserver(self):
        """上下文保持器fixture"""
        return ContextPreserver(max_context_age=timedelta(hours=1))
    
    def test_conversation_context_storage(self, context_preserver):
        """测试对话上下文存储"""
        conversation_id = "conv_123"
        
        # Create conversation context
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_456",
            agent_type="sales",
            conversation_history=[
                {"role": "user", "content": "我想要护肤品推荐"},
                {"role": "assistant", "content": "当然，请告诉我您的肌肤类型"}
            ],
            customer_profile={
                "skin_type": "oily",
                "age_range": "25-35",
                "preferences": ["natural_ingredients"]
            },
            current_state="product_inquiry",
            metadata={"language": "chinese", "urgency": "normal"}
        )
        
        # Store context
        context_preserver.store_context(conversation_id, context)
        
        # Retrieve context
        retrieved_context = context_preserver.get_context(conversation_id)
        
        assert retrieved_context is not None
        assert retrieved_context.conversation_id == conversation_id
        assert retrieved_context.customer_id == "customer_456"
        assert retrieved_context.agent_type == "sales"
        assert len(retrieved_context.conversation_history) == 2
        assert retrieved_context.customer_profile["skin_type"] == "oily"
    
    def test_context_transfer_between_providers(self, context_preserver):
        """测试供应商间上下文转移"""
        conversation_id = "conv_transfer_test"
        
        # Create original context with OpenAI
        original_context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_789",
            agent_type="sentiment",
            conversation_history=[
                {"role": "user", "content": "产品质量有问题"},
                {"role": "assistant", "content": "我理解您的担忧，能详细说明一下问题吗？"}
            ],
            current_provider=ProviderType.OPENAI,
            provider_context={
                "model": "gpt-4",
                "temperature": 0.7,
                "system_prompt": "You are a helpful customer service agent"
            }
        )
        
        context_preserver.store_context(conversation_id, original_context)
        
        # Transfer to Anthropic
        transferred_context = context_preserver.transfer_context(
            conversation_id=conversation_id,
            from_provider=ProviderType.OPENAI,
            to_provider=ProviderType.ANTHROPIC
        )
        
        assert transferred_context is not None
        assert transferred_context.current_provider == ProviderType.ANTHROPIC
        assert transferred_context.conversation_history == original_context.conversation_history
        assert transferred_context.customer_profile == original_context.customer_profile
        
        # Provider-specific context should be adapted
        assert "claude" in transferred_context.provider_context.get("model", "").lower() or \
               transferred_context.provider_context.get("model") == "auto"
    
    def test_context_continuity_preservation(self, context_preserver):
        """测试上下文连续性保持"""
        conversation_id = "conv_continuity_test"
        
        # Create context with conversation state
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_continuity",
            agent_type="product",
            conversation_history=[
                {"role": "user", "content": "我在寻找抗衰老产品"},
                {"role": "assistant", "content": "我推荐以下几种成分..."},
                {"role": "user", "content": "这些成分安全吗？"}
            ],
            current_state="safety_inquiry",
            pending_actions=["ingredient_safety_check", "provide_certifications"],
            customer_profile={
                "age_range": "45-55",
                "skin_concerns": ["aging", "wrinkles"],
                "safety_conscious": True
            }
        )
        
        context_preserver.store_context(conversation_id, context)
        
        # Ensure continuity data preserved
        continuity_data = context_preserver.extract_continuity_data(conversation_id)
        
        assert continuity_data["current_state"] == "safety_inquiry"
        assert "ingredient_safety_check" in continuity_data["pending_actions"]
        assert continuity_data["customer_profile"]["safety_conscious"] is True
        assert len(continuity_data["conversation_summary"]) > 0
    
    def test_context_expiration(self, context_preserver):
        """测试上下文过期处理"""
        conversation_id = "conv_expiry_test"
        
        # Create context
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_expiry",
            agent_type="memory"
        )
        
        # Mock old timestamp
        context.created_at = datetime.now() - timedelta(hours=2)
        context.last_updated = datetime.now() - timedelta(hours=2)
        
        context_preserver.store_context(conversation_id, context)
        
        # Try to retrieve expired context
        retrieved_context = context_preserver.get_context(conversation_id)
        
        # Should return None for expired context
        assert retrieved_context is None
        
        # Should be cleaned up
        assert conversation_id not in context_preserver.contexts
    
    def test_context_compression_for_long_conversations(self, context_preserver):
        """测试长对话上下文压缩"""
        conversation_id = "conv_long_test"
        
        # Create context with very long conversation history
        long_history = []
        for i in range(100):
            long_history.extend([
                {"role": "user", "content": f"用户消息 {i}"},
                {"role": "assistant", "content": f"助手回复 {i}"}
            ])
        
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_long",
            agent_type="sales",
            conversation_history=long_history
        )
        
        # Store and compress
        compressed_context = context_preserver.compress_context(context)
        
        # Should retain essential information but reduce size
        assert len(compressed_context.conversation_history) < len(long_history)
        assert compressed_context.conversation_summary is not None
        assert len(compressed_context.conversation_summary) > 0
        
        # Should preserve recent messages
        recent_messages = compressed_context.conversation_history[-10:]
        assert len(recent_messages) == 10


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
    # 运行基础故障转移测试
    async def run_basic_failover_tests():
        print("运行基础故障转移测试...")
        
        # 测试断路器
        circuit_breaker = CircuitBreaker(failure_threshold=3)
        assert circuit_breaker.state == CircuitState.CLOSED
        print(f"断路器初始化成功: {circuit_breaker.state}")
        
        # 测试故障检测器
        failure_detector = FailureDetector()
        failure_detector.record_result(
            provider=ProviderType.OPENAI,
            success=False,
            latency_ms=5000,
            error_message="Test error"
        )
        patterns = failure_detector.detect_failure_patterns(ProviderType.OPENAI)
        print(f"故障检测器工作正常: {len(patterns)} 个模式检测到")
        
        # 测试上下文保持器
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
        
        # 测试恢复管理器
        recovery_manager = RecoveryManager()
        strategy = recovery_manager.select_recovery_strategy(
            provider=ProviderType.OPENAI,
            error=ProviderError("Test", ProviderType.OPENAI, "test"),
            failure_pattern=FailurePattern(FailureType.TIMEOUT, 0.5, 1)
        )
        print(f"恢复管理器工作正常: {strategy}")
        
        print("基础故障转移测试完成!")
    
    asyncio.run(run_basic_failover_tests())