"""
供应商健康监控系统综合测试套件

该测试套件为多LLM供应商健康监控系统提供全面的测试覆盖，包括:
- 供应商生命周期管理测试
- 健康状态监控和检测测试
- 统计数据收集和分析测试
- 性能指标追踪测试
- 告警和通知系统测试
- 自动恢复机制测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from src.llm.provider_manager import ProviderManager
from src.llm.provider_manager.health_monitor import HealthMonitor, HealthStatus
from src.llm.provider_manager.lifecycle_manager import LifecycleManager, ProviderState
from src.llm.provider_manager.stats_collector import StatsCollector, PerformanceMetrics
from src.llm.provider_config import ProviderType, GlobalProviderConfig, ProviderConfig
from src.llm.base_provider import ProviderHealth, ProviderError


class TestHealthMonitor:
    """测试健康监控器功能"""
    
    @pytest.fixture
    def health_monitor(self):
        """健康监控器fixture"""
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
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="health_test"
        )
        return HealthMonitor(config)
    
    @pytest.mark.asyncio
    async def test_provider_health_check(self, health_monitor):
        """测试供应商健康检查"""
        # Mock provider responses
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=ProviderHealth(
            provider=ProviderType.OPENAI,
            status="healthy",
            last_check=datetime.now(),
            latency_ms=800,
            error_rate=0.02,
            success_rate=0.98,
            metadata={"api_version": "v1", "region": "us-east-1"}
        ))
        
        with patch.object(health_monitor, '_get_provider', return_value=mock_provider):
            health_result = await health_monitor.check_provider_health(ProviderType.OPENAI)
            
            assert health_result.provider == ProviderType.OPENAI
            assert health_result.status == "healthy"
            assert health_result.latency_ms == 800
            assert health_result.success_rate == 0.98
            assert health_result.is_healthy()
    
    @pytest.mark.asyncio
    async def test_unhealthy_provider_detection(self, health_monitor):
        """测试不健康供应商检测"""
        # Mock unhealthy provider
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=ProviderHealth(
            provider=ProviderType.ANTHROPIC,
            status="unhealthy",
            last_check=datetime.now(),
            latency_ms=3000,  # High latency
            error_rate=0.25,  # High error rate
            success_rate=0.75,
            metadata={"last_error": "Connection timeout", "consecutive_failures": 5}
        ))
        
        with patch.object(health_monitor, '_get_provider', return_value=mock_provider):
            health_result = await health_monitor.check_provider_health(ProviderType.ANTHROPIC)
            
            assert health_result.provider == ProviderType.ANTHROPIC
            assert health_result.status == "unhealthy"
            assert health_result.latency_ms == 3000
            assert health_result.error_rate == 0.25
            assert not health_result.is_healthy()
            assert health_result.metadata["consecutive_failures"] == 5
    
    @pytest.mark.asyncio
    async def test_periodic_health_monitoring(self, health_monitor):
        """测试定期健康监控"""
        # Mock multiple providers
        providers = {
            ProviderType.OPENAI: Mock(),
            ProviderType.ANTHROPIC: Mock()
        }
        
        # Setup mock health responses
        providers[ProviderType.OPENAI].health_check = AsyncMock(return_value=ProviderHealth(
            provider=ProviderType.OPENAI,
            status="healthy",
            last_check=datetime.now(),
            latency_ms=700,
            success_rate=0.99
        ))
        
        providers[ProviderType.ANTHROPIC].health_check = AsyncMock(return_value=ProviderHealth(
            provider=ProviderType.ANTHROPIC,
            status="degraded",
            last_check=datetime.now(),
            latency_ms=1500,
            success_rate=0.92
        ))
        
        with patch.object(health_monitor, '_get_all_providers', return_value=providers):
            # Run periodic health check
            health_results = await health_monitor.run_periodic_health_check()
            
            assert len(health_results) == 2
            assert health_results[ProviderType.OPENAI].status == "healthy"
            assert health_results[ProviderType.ANTHROPIC].status == "degraded"
            
            # Verify all providers were checked
            providers[ProviderType.OPENAI].health_check.assert_called_once()
            providers[ProviderType.ANTHROPIC].health_check.assert_called_once()
    
    def test_health_status_aggregation(self, health_monitor):
        """测试健康状态聚合"""
        # Mock health data for multiple providers
        health_data = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=800,
                success_rate=0.98
            ),
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="healthy",
                latency_ms=600,
                success_rate=0.99
            ),
            ProviderType.GEMINI: ProviderHealth(
                provider=ProviderType.GEMINI,
                status="unhealthy",
                latency_ms=2500,
                success_rate=0.85
            )
        }
        
        overall_health = health_monitor.aggregate_health_status(health_data)
        
        assert overall_health["total_providers"] == 3
        assert overall_health["healthy_providers"] == 2
        assert overall_health["unhealthy_providers"] == 1
        assert overall_health["overall_status"] == "degraded"  # Mixed health
        assert overall_health["avg_latency"] == (800 + 600 + 2500) / 3
        assert overall_health["avg_success_rate"] == (0.98 + 0.99 + 0.85) / 3
    
    def test_health_threshold_configuration(self, health_monitor):
        """测试健康阈值配置"""
        # Configure custom health thresholds
        health_monitor.configure_thresholds({
            "latency_threshold_ms": 1000,
            "error_rate_threshold": 0.1,
            "success_rate_threshold": 0.95
        })
        
        # Test provider that meets thresholds
        healthy_provider = ProviderHealth(
            provider=ProviderType.OPENAI,
            status="unknown",  # Will be determined by thresholds
            latency_ms=800,
            error_rate=0.05,
            success_rate=0.98
        )
        
        is_healthy = health_monitor._evaluate_health_status(healthy_provider)
        assert is_healthy is True
        
        # Test provider that exceeds thresholds
        unhealthy_provider = ProviderHealth(
            provider=ProviderType.ANTHROPIC,
            status="unknown",
            latency_ms=1500,  # Exceeds threshold
            error_rate=0.15,  # Exceeds threshold
            success_rate=0.90  # Below threshold
        )
        
        is_healthy = health_monitor._evaluate_health_status(unhealthy_provider)
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_health_change_detection(self, health_monitor):
        """测试健康状态变化检测"""
        provider = ProviderType.OPENAI
        
        # Initial healthy state
        initial_health = ProviderHealth(
            provider=provider,
            status="healthy",
            latency_ms=700,
            success_rate=0.99
        )
        
        health_monitor._store_health_record(provider, initial_health)
        
        # Changed to unhealthy state
        degraded_health = ProviderHealth(
            provider=provider,
            status="unhealthy",
            latency_ms=2000,
            success_rate=0.80
        )
        
        # Detect health change
        change_detected = health_monitor.detect_health_change(provider, degraded_health)
        
        assert change_detected is True
        assert health_monitor.get_health_trend(provider) == "degrading"
        
        # Store the new state
        health_monitor._store_health_record(provider, degraded_health)
        
        # Recovery to healthy state
        recovered_health = ProviderHealth(
            provider=provider,
            status="healthy",
            latency_ms=750,
            success_rate=0.97
        )
        
        recovery_detected = health_monitor.detect_health_change(provider, recovered_health)
        assert recovery_detected is True
        assert health_monitor.get_health_trend(provider) == "improving"


class TestLifecycleManager:
    """测试生命周期管理器功能"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """生命周期管理器fixture"""
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
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="lifecycle_test"
        )
        return LifecycleManager(config)
    
    def test_provider_state_transitions(self, lifecycle_manager):
        """测试供应商状态转换"""
        provider = ProviderType.OPENAI
        
        # Initial state should be INITIALIZING
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.INITIALIZING
        
        # Transition to ACTIVE
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.ACTIVE
        
        # Transition to DEGRADED
        lifecycle_manager.transition_provider_state(provider, ProviderState.DEGRADED)
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.DEGRADED
        
        # Transition to FAILED
        lifecycle_manager.transition_provider_state(provider, ProviderState.FAILED)
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.FAILED
        
        # Transition to RECOVERY
        lifecycle_manager.transition_provider_state(provider, ProviderState.RECOVERY)
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.RECOVERY
        
        # Back to ACTIVE
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.ACTIVE
    
    def test_invalid_state_transitions(self, lifecycle_manager):
        """测试无效状态转换"""
        provider = ProviderType.ANTHROPIC
        
        # Try invalid transition from INITIALIZING to RECOVERY
        with pytest.raises(ValueError) as exc_info:
            lifecycle_manager.transition_provider_state(provider, ProviderState.RECOVERY)
        
        assert "Invalid state transition" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, lifecycle_manager):
        """测试供应商初始化"""
        provider = ProviderType.OPENAI
        
        # Mock provider initialization
        mock_provider = Mock()
        mock_provider.initialize = AsyncMock(return_value=True)
        mock_provider.health_check = AsyncMock(return_value=ProviderHealth(
            provider=provider,
            status="healthy",
            latency_ms=800,
            success_rate=0.99
        ))
        
        with patch.object(lifecycle_manager, '_get_provider', return_value=mock_provider):
            success = await lifecycle_manager.initialize_provider(provider)
            
            assert success is True
            assert lifecycle_manager.get_provider_state(provider) == ProviderState.ACTIVE
            mock_provider.initialize.assert_called_once()
            mock_provider.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_provider_shutdown(self, lifecycle_manager):
        """测试供应商关闭"""
        provider = ProviderType.ANTHROPIC
        
        # Set provider to active first
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        
        # Mock provider shutdown
        mock_provider = Mock()
        mock_provider.shutdown = AsyncMock(return_value=True)
        
        with patch.object(lifecycle_manager, '_get_provider', return_value=mock_provider):
            success = await lifecycle_manager.shutdown_provider(provider)
            
            assert success is True
            assert lifecycle_manager.get_provider_state(provider) == ProviderState.SHUTDOWN
            mock_provider.shutdown.assert_called_once()
    
    def test_provider_state_history(self, lifecycle_manager):
        """测试供应商状态历史"""
        provider = ProviderType.OPENAI
        
        # Perform several state transitions
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        lifecycle_manager.transition_provider_state(provider, ProviderState.DEGRADED)
        lifecycle_manager.transition_provider_state(provider, ProviderState.RECOVERY)
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        
        # Get state history
        history = lifecycle_manager.get_provider_state_history(provider)
        
        assert len(history) >= 4
        assert history[-1]["state"] == ProviderState.ACTIVE
        assert history[-2]["state"] == ProviderState.RECOVERY
        assert history[-3]["state"] == ProviderState.DEGRADED
        
        # Verify timestamps are in correct order
        for i in range(len(history) - 1):
            assert history[i]["timestamp"] <= history[i + 1]["timestamp"]
    
    def test_bulk_provider_management(self, lifecycle_manager):
        """测试批量供应商管理"""
        providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        
        # Initialize all providers
        with patch.object(lifecycle_manager, 'initialize_provider', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            
            asyncio.run(lifecycle_manager.initialize_all_providers())
            
            # Should have called initialize for each provider
            assert mock_init.call_count == len(providers)
        
        # Shutdown all providers
        with patch.object(lifecycle_manager, 'shutdown_provider', new_callable=AsyncMock) as mock_shutdown:
            mock_shutdown.return_value = True
            
            asyncio.run(lifecycle_manager.shutdown_all_providers())
            
            # Should have called shutdown for each provider
            assert mock_shutdown.call_count == len(providers)


class TestStatsCollector:
    """测试统计数据收集器功能"""
    
    @pytest.fixture
    def stats_collector(self):
        """统计数据收集器fixture"""
        return StatsCollector()
    
    def test_performance_metrics_recording(self, stats_collector):
        """测试性能指标记录"""
        provider = ProviderType.OPENAI
        
        # Record multiple performance metrics
        for i in range(10):
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=datetime.now(),
                latency_ms=800 + (i * 10),
                success=i < 8,  # 80% success rate
                cost=0.002,
                input_tokens=100,
                output_tokens=50,
                metadata={"request_id": f"req_{i}"}
            )
            
            stats_collector.record_performance_metrics(metrics)
        
        # Get aggregated statistics
        stats = stats_collector.get_provider_stats(provider)
        
        assert stats["total_requests"] == 10
        assert stats["success_rate"] == 0.8
        assert stats["avg_latency_ms"] == 800 + (9 * 10) / 2  # Average of range
        assert stats["total_cost"] == 0.02  # 10 * 0.002
        assert stats["total_tokens"] == 1500  # 10 * 150
    
    def test_time_window_statistics(self, stats_collector):
        """测试时间窗口统计"""
        provider = ProviderType.ANTHROPIC
        base_time = datetime.now()
        
        # Record metrics over different time periods
        for i in range(20):
            timestamp = base_time - timedelta(hours=i)
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=timestamp,
                latency_ms=600,
                success=True,
                cost=0.003
            )
            
            stats_collector.record_performance_metrics(metrics)
        
        # Get statistics for last 12 hours
        recent_stats = stats_collector.get_provider_stats(
            provider=provider,
            time_window=timedelta(hours=12)
        )
        
        # Should only include 12 most recent records
        assert recent_stats["total_requests"] == 12
        
        # Get statistics for last 24 hours
        daily_stats = stats_collector.get_provider_stats(
            provider=provider,
            time_window=timedelta(hours=24)
        )
        
        # Should include all 20 records
        assert daily_stats["total_requests"] == 20
    
    def test_error_rate_calculation(self, stats_collector):
        """测试错误率计算"""
        provider = ProviderType.GEMINI
        
        # Record mixed success/failure metrics
        success_pattern = [True, True, False, True, False, True, True, False, True, True]
        
        for i, success in enumerate(success_pattern):
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=datetime.now(),
                latency_ms=700,
                success=success,
                cost=0.001,
                error_type="timeout" if not success else None
            )
            
            stats_collector.record_performance_metrics(metrics)
        
        stats = stats_collector.get_provider_stats(provider)
        
        # Calculate expected error rate: 3 failures out of 10 = 0.3
        assert stats["error_rate"] == 0.3
        assert stats["success_rate"] == 0.7
        
        # Get error breakdown
        error_breakdown = stats_collector.get_error_breakdown(provider)
        assert error_breakdown["timeout"] == 3
        assert error_breakdown["total_errors"] == 3
    
    def test_cost_analysis_statistics(self, stats_collector):
        """测试成本分析统计"""
        provider = ProviderType.DEEPSEEK
        
        # Record metrics with varying costs
        costs = [0.0005, 0.0008, 0.0012, 0.0006, 0.001]
        
        for cost in costs:
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=datetime.now(),
                latency_ms=900,
                success=True,
                cost=cost,
                input_tokens=100,
                output_tokens=50
            )
            
            stats_collector.record_performance_metrics(metrics)
        
        stats = stats_collector.get_provider_stats(provider)
        
        # Verify cost calculations
        total_cost = sum(costs)
        assert stats["total_cost"] == total_cost
        assert stats["avg_cost_per_request"] == total_cost / len(costs)
        assert stats["cost_per_token"] == total_cost / (len(costs) * 150)  # 150 tokens per request
    
    def test_performance_trends(self, stats_collector):
        """测试性能趋势分析"""
        provider = ProviderType.OPENAI
        base_time = datetime.now()
        
        # Record metrics showing improving performance over time
        for i in range(24):  # 24 hours of data
            # Latency improves over time
            latency = 1000 - (i * 20)  # Decreasing latency
            # Success rate improves over time
            success_rate = 0.8 + (i * 0.008)  # Increasing success rate
            
            timestamp = base_time - timedelta(hours=23-i)
            
            # Record multiple metrics per hour
            for j in range(5):
                metrics = PerformanceMetrics(
                    provider=provider,
                    timestamp=timestamp + timedelta(minutes=j*10),
                    latency_ms=latency + random.randint(-50, 50),
                    success=random.random() < success_rate,
                    cost=0.002
                )
                
                stats_collector.record_performance_metrics(metrics)
        
        # Analyze trends
        trends = stats_collector.analyze_performance_trends(
            provider=provider,
            time_window=timedelta(hours=24)
        )
        
        assert "latency_trend" in trends
        assert "success_rate_trend" in trends
        assert trends["latency_trend"] == "improving"  # Latency decreasing
        assert trends["success_rate_trend"] == "improving"  # Success rate increasing
    
    def test_comparative_provider_analysis(self, stats_collector):
        """测试供应商比较分析"""
        providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.GEMINI]
        
        # Record different performance characteristics for each provider
        provider_configs = {
            ProviderType.OPENAI: {"latency": 800, "success_rate": 0.98, "cost": 0.002},
            ProviderType.ANTHROPIC: {"latency": 600, "success_rate": 0.99, "cost": 0.003},
            ProviderType.GEMINI: {"latency": 700, "success_rate": 0.97, "cost": 0.001}
        }
        
        for provider, config in provider_configs.items():
            for i in range(10):
                metrics = PerformanceMetrics(
                    provider=provider,
                    timestamp=datetime.now(),
                    latency_ms=config["latency"],
                    success=random.random() < config["success_rate"],
                    cost=config["cost"]
                )
                
                stats_collector.record_performance_metrics(metrics)
        
        # Get comparative analysis
        comparison = stats_collector.compare_providers(providers)
        
        assert "fastest_provider" in comparison
        assert "most_reliable_provider" in comparison
        assert "most_cost_effective_provider" in comparison
        
        # Anthropic should be fastest (lowest latency)
        assert comparison["fastest_provider"] == ProviderType.ANTHROPIC
        
        # Gemini should be most cost-effective (lowest cost)
        assert comparison["most_cost_effective_provider"] == ProviderType.GEMINI


class TestIntegratedMonitoringScenarios:
    """测试集成监控场景"""
    
    @pytest.fixture
    def monitoring_system(self):
        """完整监控系统fixture"""
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
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="monitoring_test"
        )
        
        return {
            "health_monitor": HealthMonitor(config),
            "lifecycle_manager": LifecycleManager(config),
            "stats_collector": StatsCollector()
        }
    
    @pytest.mark.asyncio
    async def test_provider_failure_and_recovery_workflow(self, monitoring_system):
        """测试供应商故障和恢复工作流"""
        health_monitor = monitoring_system["health_monitor"]
        lifecycle_manager = monitoring_system["lifecycle_manager"]
        stats_collector = monitoring_system["stats_collector"]
        
        provider = ProviderType.OPENAI
        
        # 1. Initial healthy state
        lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        
        # 2. Simulate provider degradation
        for i in range(5):
            # Record degrading performance
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=datetime.now(),
                latency_ms=1000 + (i * 200),  # Increasing latency
                success=i < 2,  # Decreasing success rate
                cost=0.002
            )
            stats_collector.record_performance_metrics(metrics)
        
        # 3. Health check detects issues
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=ProviderHealth(
            provider=provider,
            status="unhealthy",
            latency_ms=1800,
            error_rate=0.6,
            success_rate=0.4
        ))
        
        with patch.object(health_monitor, '_get_provider', return_value=mock_provider):
            health_result = await health_monitor.check_provider_health(provider)
            
            # 4. Trigger state transition to FAILED
            if not health_result.is_healthy():
                lifecycle_manager.transition_provider_state(provider, ProviderState.FAILED)
        
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.FAILED
        
        # 5. Simulate recovery process
        lifecycle_manager.transition_provider_state(provider, ProviderState.RECOVERY)
        
        # 6. Record improving metrics during recovery
        for i in range(5):
            metrics = PerformanceMetrics(
                provider=provider,
                timestamp=datetime.now(),
                latency_ms=1000 - (i * 150),  # Decreasing latency
                success=True,  # Full success
                cost=0.002
            )
            stats_collector.record_performance_metrics(metrics)
        
        # 7. Health check confirms recovery
        mock_provider.health_check = AsyncMock(return_value=ProviderHealth(
            provider=provider,
            status="healthy",
            latency_ms=700,
            error_rate=0.0,
            success_rate=1.0
        ))
        
        with patch.object(health_monitor, '_get_provider', return_value=mock_provider):
            recovery_health = await health_monitor.check_provider_health(provider)
            
            # 8. Transition back to ACTIVE
            if recovery_health.is_healthy():
                lifecycle_manager.transition_provider_state(provider, ProviderState.ACTIVE)
        
        assert lifecycle_manager.get_provider_state(provider) == ProviderState.ACTIVE
        
        # 9. Verify complete workflow was tracked
        state_history = lifecycle_manager.get_provider_state_history(provider)
        state_progression = [entry["state"] for entry in state_history]
        
        assert ProviderState.ACTIVE in state_progression
        assert ProviderState.FAILED in state_progression
        assert ProviderState.RECOVERY in state_progression
        
        # Final state should be ACTIVE
        assert state_progression[-1] == ProviderState.ACTIVE
    
    def test_multi_provider_monitoring_dashboard(self, monitoring_system):
        """测试多供应商监控仪表板数据"""
        health_monitor = monitoring_system["health_monitor"]
        stats_collector = monitoring_system["stats_collector"]
        
        providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.GEMINI]
        
        # Simulate different performance profiles for dashboard
        provider_profiles = {
            ProviderType.OPENAI: {
                "health": ProviderHealth(
                    provider=ProviderType.OPENAI,
                    status="healthy",
                    latency_ms=800,
                    success_rate=0.98
                ),
                "stats": {"total_requests": 1000, "total_cost": 2.0}
            },
            ProviderType.ANTHROPIC: {
                "health": ProviderHealth(
                    provider=ProviderType.ANTHROPIC,
                    status="healthy",
                    latency_ms=600,
                    success_rate=0.99
                ),
                "stats": {"total_requests": 600, "total_cost": 1.8}
            },
            ProviderType.GEMINI: {
                "health": ProviderHealth(
                    provider=ProviderType.GEMINI,
                    status="degraded",
                    latency_ms=1200,
                    success_rate=0.94
                ),
                "stats": {"total_requests": 800, "total_cost": 0.8}
            }
        }
        
        # Collect dashboard data
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "providers": {},
            "overall_metrics": {
                "total_requests": 0,
                "total_cost": 0,
                "avg_success_rate": 0,
                "healthy_providers": 0
            }
        }
        
        for provider, profile in provider_profiles.items():
            dashboard_data["providers"][provider.value] = {
                "health": {
                    "status": profile["health"].status,
                    "latency_ms": profile["health"].latency_ms,
                    "success_rate": profile["health"].success_rate
                },
                "stats": profile["stats"]
            }
            
            # Update overall metrics
            dashboard_data["overall_metrics"]["total_requests"] += profile["stats"]["total_requests"]
            dashboard_data["overall_metrics"]["total_cost"] += profile["stats"]["total_cost"]
            dashboard_data["overall_metrics"]["avg_success_rate"] += profile["health"].success_rate
            
            if profile["health"].status in ["healthy", "degraded"]:
                dashboard_data["overall_metrics"]["healthy_providers"] += 1
        
        # Calculate averages
        dashboard_data["overall_metrics"]["avg_success_rate"] /= len(providers)
        
        # Verify dashboard data structure and values
        assert dashboard_data["overall_metrics"]["total_requests"] == 2400
        assert dashboard_data["overall_metrics"]["total_cost"] == 4.6
        assert dashboard_data["overall_metrics"]["healthy_providers"] == 3
        assert len(dashboard_data["providers"]) == 3
        
        # Best performing provider should be Anthropic (highest success rate, low latency)
        anthropic_data = dashboard_data["providers"]["anthropic"]
        assert anthropic_data["health"]["success_rate"] == 0.99
        assert anthropic_data["health"]["latency_ms"] == 600


if __name__ == "__main__":
    # 运行基础监控测试
    async def run_basic_monitoring_tests():
        print("运行基础供应商健康监控测试...")
        
        # 测试健康监控器
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key="test-key",
                    models=["gpt-4"]
                )
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="test"
        )
        
        health_monitor = HealthMonitor(config)
        print(f"健康监控器初始化成功")
        
        # 测试生命周期管理器
        lifecycle_manager = LifecycleManager(config)
        lifecycle_manager.transition_provider_state(ProviderType.OPENAI, ProviderState.ACTIVE)
        assert lifecycle_manager.get_provider_state(ProviderType.OPENAI) == ProviderState.ACTIVE
        print(f"生命周期管理器工作正常")
        
        # 测试统计收集器
        stats_collector = StatsCollector()
        metrics = PerformanceMetrics(
            provider=ProviderType.OPENAI,
            timestamp=datetime.now(),
            latency_ms=800,
            success=True,
            cost=0.002
        )
        stats_collector.record_performance_metrics(metrics)
        stats = stats_collector.get_provider_stats(ProviderType.OPENAI)
        assert stats["total_requests"] == 1
        print(f"统计收集器工作正常")
        
        print("基础供应商健康监控测试完成!")
    
    asyncio.run(run_basic_monitoring_tests())