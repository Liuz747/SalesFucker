"""
路由学习引擎测试套件

该测试套件专门测试路由系统的学习和适应能力:
- 学习引擎性能指标追踪
- 供应商排名学习
- 自适应阈值调整
- 上下文感知学习
"""

import pytest

@pytest.mark.skip(reason="Feature removed in simplified LLM system")
import random
from unittest.mock import Mock
from datetime import datetime, timedelta

from src.llm.intelligent_router.learning_engine import LearningEngine, PerformanceMetrics
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType


class TestPerformanceMetricsTracking:
    """测试性能指标追踪"""
    
    @pytest.fixture
    def learning_engine(self):
        """学习引擎fixture"""
        return LearningEngine()
    
    def test_interaction_recording(self, learning_engine):
        """测试交互记录"""
        learning_engine.record_interaction(
            provider=ProviderType.OPENAI,
            agent_type="sales",
            latency_ms=800,
            success=True,
            user_satisfaction=0.9,
            cost=0.002,
            metadata={"language": "chinese"}
        )
        
        learning_engine.record_interaction(
            provider=ProviderType.ANTHROPIC,
            agent_type="sales",
            latency_ms=600,
            success=True,
            user_satisfaction=0.95,
            cost=0.003,
            metadata={"language": "chinese"}
        )
        
        # Verify recording worked
        metrics = learning_engine.get_performance_metrics(
            provider=ProviderType.ANTHROPIC,
            agent_type="sales",
            time_window=timedelta(hours=24)
        )
        
        assert metrics.avg_latency == 600
        assert metrics.success_rate == 1.0
        assert metrics.avg_satisfaction == 0.95
        assert metrics.total_interactions == 1
    
    def test_metrics_aggregation(self, learning_engine):
        """测试指标聚合"""
        # Record multiple interactions
        latencies = [600, 650, 580, 620, 590]
        satisfactions = [0.9, 0.95, 0.85, 0.92, 0.88]
        
        for latency, satisfaction in zip(latencies, satisfactions):
            learning_engine.record_interaction(
                provider=ProviderType.ANTHROPIC,
                agent_type="product",
                latency_ms=latency,
                success=True,
                user_satisfaction=satisfaction,
                cost=0.003
            )
        
        metrics = learning_engine.get_performance_metrics(
            provider=ProviderType.ANTHROPIC,
            agent_type="product",
            time_window=timedelta(hours=24)
        )
        
        # Check aggregated values
        expected_avg_latency = sum(latencies) / len(latencies)
        expected_avg_satisfaction = sum(satisfactions) / len(satisfactions)
        
        assert abs(metrics.avg_latency - expected_avg_latency) < 1
        assert abs(metrics.avg_satisfaction - expected_avg_satisfaction) < 0.01
        assert metrics.total_interactions == len(latencies)


class TestProviderRankingLearning:
    """测试供应商排名学习"""
    
    @pytest.fixture
    def populated_learning_engine(self):
        """预填充数据的学习引擎"""
        engine = LearningEngine()
        
        # Record interactions for different providers
        providers_data = [
            (ProviderType.OPENAI, 800, True, 0.85, 0.002),
            (ProviderType.ANTHROPIC, 600, True, 0.92, 0.003),
            (ProviderType.GEMINI, 900, True, 0.88, 0.001),
            (ProviderType.DEEPSEEK, 1200, False, 0.70, 0.0005)
        ]
        
        for provider, latency, success, satisfaction, cost in providers_data:
            for _ in range(10):  # Multiple interactions per provider
                engine.record_interaction(
                    provider=provider,
                    agent_type="sentiment",
                    latency_ms=latency + random.randint(-100, 100),
                    success=success,
                    user_satisfaction=satisfaction + random.uniform(-0.1, 0.1),
                    cost=cost
                )
        
        return engine
    
    def test_provider_ranking_accuracy(self, populated_learning_engine):
        """测试供应商排名准确性"""
        rankings = populated_learning_engine.get_provider_rankings(agent_type="sentiment")
        
        # Anthropic should rank highest (fast, reliable, high satisfaction)
        assert rankings[0] == ProviderType.ANTHROPIC
        
        # DeepSeek should rank lowest (slow, unreliable, low satisfaction)
        assert rankings[-1] == ProviderType.DEEPSEEK
    
    def test_ranking_stability(self, populated_learning_engine):
        """测试排名稳定性"""
        # Get rankings multiple times
        rankings1 = populated_learning_engine.get_provider_rankings(agent_type="sentiment")
        rankings2 = populated_learning_engine.get_provider_rankings(agent_type="sentiment")
        
        # Rankings should be consistent
        assert rankings1 == rankings2
    
    def test_agent_specific_rankings(self, populated_learning_engine):
        """测试智能体特定排名"""
        # Record different performance for different agents
        populated_learning_engine.record_interaction(
            provider=ProviderType.DEEPSEEK,
            agent_type="product",  # Different agent
            latency_ms=800,  # Better performance for this agent
            success=True,
            user_satisfaction=0.9,
            cost=0.0005
        )
        
        sentiment_rankings = populated_learning_engine.get_provider_rankings(agent_type="sentiment")
        product_rankings = populated_learning_engine.get_provider_rankings(agent_type="product")
        
        # Rankings should differ by agent type
        assert sentiment_rankings != product_rankings


class TestAdaptiveThresholdAdjustment:
    """测试自适应阈值调整"""
    
    @pytest.fixture
    def threshold_learning_engine(self):
        """用于阈值调整测试的学习引擎"""
        return LearningEngine()
    
    def test_latency_threshold_adaptation(self, threshold_learning_engine):
        """测试延迟阈值适应"""
        # Record interactions with high latency but good satisfaction
        for _ in range(20):
            threshold_learning_engine.record_interaction(
                provider=ProviderType.OPENAI,
                agent_type="product",
                latency_ms=1500,  # High latency
                success=True,
                user_satisfaction=0.9,  # But high satisfaction
                cost=0.002
            )
        
        thresholds = threshold_learning_engine.get_adaptive_thresholds(agent_type="product")
        
        # Latency threshold should adapt higher
        assert thresholds["max_acceptable_latency"] > 1000
        assert thresholds["min_acceptable_satisfaction"] <= 0.9
    
    def test_cost_threshold_adaptation(self, threshold_learning_engine):
        """测试成本阈值适应"""
        # Record interactions with higher cost but good results
        for _ in range(15):
            threshold_learning_engine.record_interaction(
                provider=ProviderType.ANTHROPIC,
                agent_type="sales",
                latency_ms=600,
                success=True,
                user_satisfaction=0.95,
                cost=0.005  # Higher cost
            )
        
        thresholds = threshold_learning_engine.get_adaptive_thresholds(agent_type="sales")
        
        # Cost threshold should adapt higher
        assert thresholds.get("max_acceptable_cost", 0) > 0.003


class TestContextAwareLearning:
    """测试上下文感知学习"""
    
    @pytest.fixture
    def context_learning_engine(self):
        """用于上下文学习测试的引擎"""
        return LearningEngine()
    
    def test_language_context_learning(self, context_learning_engine):
        """测试语言上下文学习"""
        # Record Chinese language interactions
        for _ in range(15):
            context_learning_engine.record_interaction(
                provider=ProviderType.DEEPSEEK,
                agent_type="product",
                latency_ms=1000,
                success=True,
                user_satisfaction=0.95,
                cost=0.0005,
                metadata={"language": "chinese", "region": "china"}
            )
        
        # Record English language interactions
        for _ in range(15):
            context_learning_engine.record_interaction(
                provider=ProviderType.OPENAI,
                agent_type="product",
                latency_ms=800,
                success=True,
                user_satisfaction=0.9,
                cost=0.002,
                metadata={"language": "english", "region": "us"}
            )
        
        # Get context-specific recommendations
        chinese_rec = context_learning_engine.get_context_recommendations(
            agent_type="product",
            context={"language": "chinese", "region": "china"}
        )
        
        english_rec = context_learning_engine.get_context_recommendations(
            agent_type="product",
            context={"language": "english", "region": "us"}
        )
        
        # Should recommend different providers for different contexts
        assert chinese_rec["preferred_provider"] == ProviderType.DEEPSEEK
        assert english_rec["preferred_provider"] == ProviderType.OPENAI
    
    def test_temporal_context_learning(self, context_learning_engine):
        """测试时间上下文学习"""
        # Record interactions with time-based metadata
        for hour in range(9, 18):  # Business hours
            context_learning_engine.record_interaction(
                provider=ProviderType.OPENAI,
                agent_type="sales",
                latency_ms=700,
                success=True,
                user_satisfaction=0.9,
                cost=0.002,
                metadata={"hour": hour, "is_business_hours": True}
            )
        
        for hour in [20, 21, 22]:  # Evening hours
            context_learning_engine.record_interaction(
                provider=ProviderType.DEEPSEEK,
                agent_type="sales",
                latency_ms=1000,  # Slower but cheaper
                success=True,
                user_satisfaction=0.85,
                cost=0.0005,
                metadata={"hour": hour, "is_business_hours": False}
            )
        
        # Get time-specific recommendations
        business_rec = context_learning_engine.get_context_recommendations(
            agent_type="sales",
            context={"hour": 14, "is_business_hours": True}
        )
        
        evening_rec = context_learning_engine.get_context_recommendations(
            agent_type="sales",
            context={"hour": 21, "is_business_hours": False}
        )
        
        # Should adapt to time-based patterns
        assert business_rec["preferred_provider"] == ProviderType.OPENAI
        assert evening_rec["preferred_provider"] == ProviderType.DEEPSEEK


if __name__ == "__main__":
    print("路由学习引擎测试模块加载成功")
    print("测试覆盖: 性能追踪、排名学习、阈值适应、上下文学习")