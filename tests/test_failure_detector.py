"""
故障检测器(Failure Detector)组件测试套件

该测试模块专注于故障检测器的核心功能测试:
- 错误率检测和阈值监控
- 延迟峰值检测
- 连续故障模式识别
- 超时检测
- 故障模式严重程度评估
- 时间窗口过滤机制
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.failover_system.failure_detector import FailureDetector, FailurePattern
from src.llm.failover_system.models import FailureType, FailureRecord
from src.llm.provider_config import ProviderType


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


if __name__ == "__main__":
    # 运行故障检测器测试
    def run_failure_detector_tests():
        print("运行故障检测器测试...")
        
        # 测试故障检测器初始化
        failure_detector = FailureDetector()
        assert failure_detector.error_rate_threshold > 0
        print(f"故障检测器初始化成功: 阈值={failure_detector.error_rate_threshold}")
        
        # 测试故障记录
        failure_detector.record_result(
            provider=ProviderType.OPENAI,
            success=False,
            latency_ms=5000,
            error_message="Test error"
        )
        patterns = failure_detector.detect_failure_patterns(ProviderType.OPENAI)
        print(f"故障模式检测完成: {len(patterns)} 个模式")
        
        print("故障检测器测试完成!")
    
    run_failure_detector_tests()