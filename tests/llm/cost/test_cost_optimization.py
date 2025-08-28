"""
成本优化系统综合测试套件

该测试套件为多LLM成本优化系统提供全面的测试覆盖，包括:
- 成本追踪和分析功能测试
- 优化建议引擎测试
- 预算监控和告警测试
- 多供应商成本比较测试
- 成本效益分析测试
- 自适应优化策略测试
"""

import pytest

@pytest.mark.skip(reason="Feature removed in simplified LLM system")
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Note: Cost optimization removed in simplified system
from src.llm.cost_optimizer.analyzer import CostAnalyzer, UsagePattern
from src.llm.cost_optimizer.suggestion_engine import (
    SuggestionEngine, OptimizationSuggestion, SuggestionType
)
from src.llm.cost_optimizer.budget_monitor import (
    BudgetMonitor, BudgetAlert, AlertType, BudgetThreshold
)
from src.llm.cost_optimizer.models import (
    CostRecord, UsageMetrics, CostBreakdown, 
    OptimizationOpportunity, BudgetStatus
)
from src.llm.cost_optimizer.benchmark_data import BenchmarkDataManager
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.providers.base import BaseProvider


class TestCostRecord:
    """测试成本记录模型"""
    
    def test_cost_record_creation(self):
        """测试成本记录创建"""
        record = CostRecord(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost=Decimal("0.003"),
            request_id="req_123",
            tenant_id="tenant_test",
            agent_type="sales",
            timestamp=datetime.now()
        )
        
        assert record.provider == ProviderType.OPENAI
        assert record.model == "gpt-4"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.cost == Decimal("0.003")
        assert record.request_id == "req_123"
        assert record.tenant_id == "tenant_test"
        assert record.agent_type == "sales"
        assert record.total_tokens == 150
    
    def test_cost_calculation_validation(self):
        """测试成本计算验证"""
        # Valid cost record
        valid_record = CostRecord(
            provider=ProviderType.ANTHROPIC,
            model="claude-3-sonnet",
            input_tokens=200,
            output_tokens=100,
            cost=Decimal("0.006"),
            request_id="req_456"
        )
        
        assert valid_record.cost_per_token == Decimal("0.006") / 300
        assert valid_record.input_cost_ratio == Decimal("200") / Decimal("300")
        assert valid_record.output_cost_ratio == Decimal("100") / Decimal("300")
    
    def test_usage_metrics_aggregation(self):
        """测试使用指标聚合"""
        records = [
            CostRecord(
                provider=ProviderType.OPENAI,
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                cost=Decimal("0.003"),
                request_id=f"req_{i}"
            ) for i in range(10)
        ]
        
        metrics = UsageMetrics.from_records(records)
        
        assert metrics.total_requests == 10
        assert metrics.total_tokens == 1500  # 150 * 10
        assert metrics.total_cost == Decimal("0.03")  # 0.003 * 10
        assert metrics.avg_tokens_per_request == 150
        assert metrics.avg_cost_per_request == Decimal("0.003")


class TestCostAnalyzer:
    """测试成本分析器功能"""
    
    @pytest.fixture
    def cost_analyzer(self):
        """成本分析器fixture"""
        return CostAnalyzer()
    
    @pytest.fixture
    def sample_cost_records(self):
        """示例成本记录fixture"""
        base_time = datetime.now() - timedelta(days=7)
        records = []
        
        # OpenAI records
        for i in range(20):
            records.append(CostRecord(
                provider=ProviderType.OPENAI,
                model="gpt-4",
                input_tokens=100 + (i * 10),
                output_tokens=50 + (i * 5),
                cost=Decimal("0.002") + (Decimal("0.0001") * i),
                request_id=f"openai_req_{i}",
                tenant_id="test_tenant",
                agent_type="sales" if i % 2 == 0 else "product",
                timestamp=base_time + timedelta(hours=i)
            ))
        
        # Anthropic records
        for i in range(15):
            records.append(CostRecord(
                provider=ProviderType.ANTHROPIC,
                model="claude-3-sonnet",
                input_tokens=150 + (i * 8),
                output_tokens=75 + (i * 4),
                cost=Decimal("0.003") + (Decimal("0.0002") * i),
                request_id=f"anthropic_req_{i}",
                tenant_id="test_tenant",
                agent_type="compliance" if i % 3 == 0 else "sentiment",
                timestamp=base_time + timedelta(hours=i + 12)
            ))
        
        return records
    
    def test_provider_cost_breakdown(self, cost_analyzer, sample_cost_records):
        """测试供应商成本分解"""
        breakdown = cost_analyzer.analyze_provider_costs(
            records=sample_cost_records,
            time_period=timedelta(days=7)
        )
        
        assert ProviderType.OPENAI in breakdown
        assert ProviderType.ANTHROPIC in breakdown
        
        openai_breakdown = breakdown[ProviderType.OPENAI]
        anthropic_breakdown = breakdown[ProviderType.ANTHROPIC]
        
        assert openai_breakdown.total_requests == 20
        assert anthropic_breakdown.total_requests == 15
        assert openai_breakdown.total_cost > 0
        assert anthropic_breakdown.total_cost > 0
    
    def test_temporal_cost_analysis(self, cost_analyzer, sample_cost_records):
        """测试时间成本分析"""
        # Analyze hourly costs
        hourly_analysis = cost_analyzer.analyze_temporal_patterns(
            records=sample_cost_records,
            granularity="hour"
        )
        
        assert len(hourly_analysis) > 0
        assert all("hour" in entry for entry in hourly_analysis)
        assert all("cost" in entry for entry in hourly_analysis)
        assert all("requests" in entry for entry in hourly_analysis)
        
        # Analyze daily costs
        daily_analysis = cost_analyzer.analyze_temporal_patterns(
            records=sample_cost_records,
            granularity="day"
        )
        
        assert len(daily_analysis) <= len(hourly_analysis)
        total_daily_cost = sum(Decimal(str(entry["cost"])) for entry in daily_analysis)
        total_hourly_cost = sum(Decimal(str(entry["cost"])) for entry in hourly_analysis)
        assert abs(total_daily_cost - total_hourly_cost) < Decimal("0.001")
    
    def test_agent_cost_distribution(self, cost_analyzer, sample_cost_records):
        """测试智能体成本分布"""
        agent_analysis = cost_analyzer.analyze_agent_costs(sample_cost_records)
        
        expected_agents = {"sales", "product", "compliance", "sentiment"}
        assert all(agent in agent_analysis for agent in expected_agents)
        
        sales_cost = agent_analysis["sales"]
        assert sales_cost["total_requests"] > 0
        assert sales_cost["total_cost"] > 0
        assert sales_cost["avg_cost_per_request"] > 0
    
    def test_usage_pattern_detection(self, cost_analyzer, sample_cost_records):
        """测试使用模式检测"""
        patterns = cost_analyzer.detect_usage_patterns(sample_cost_records)
        
        assert len(patterns) > 0
        
        # Check for expected pattern types
        pattern_types = [p.pattern_type for p in patterns]
        assert any("high_cost_provider" in pt for pt in pattern_types)
        assert any("heavy_usage_agent" in pt for pt in pattern_types)
    
    def test_cost_efficiency_metrics(self, cost_analyzer, sample_cost_records):
        """测试成本效率指标"""
        efficiency = cost_analyzer.calculate_efficiency_metrics(sample_cost_records)
        
        assert "cost_per_token" in efficiency
        assert "cost_per_request" in efficiency
        assert "token_utilization" in efficiency
        assert "provider_efficiency" in efficiency
        
        assert efficiency["cost_per_token"] > 0
        assert efficiency["cost_per_request"] > 0
        assert 0 <= efficiency["token_utilization"] <= 1
    
    def test_cost_trend_analysis(self, cost_analyzer):
        """测试成本趋势分析"""
        # Create trending data
        base_time = datetime.now() - timedelta(days=30)
        trending_records = []
        
        for day in range(30):
            daily_cost = Decimal("0.01") + (Decimal("0.001") * day)  # Increasing trend
            for hour in range(24):
                trending_records.append(CostRecord(
                    provider=ProviderType.OPENAI,
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50,
                    cost=daily_cost / 24,
                    request_id=f"trend_req_{day}_{hour}",
                    timestamp=base_time + timedelta(days=day, hours=hour)
                ))
        
        trends = cost_analyzer.analyze_cost_trends(
            records=trending_records,
            time_period=timedelta(days=30)
        )
        
        assert "trend_direction" in trends
        assert "trend_strength" in trends
        assert "daily_change_rate" in trends
        assert trends["trend_direction"] == "increasing"
        assert trends["trend_strength"] > 0.5


class TestSuggestionEngine:
    """测试优化建议引擎"""
    
    @pytest.fixture
    def suggestion_engine(self):
        """建议引擎fixture"""
        return SuggestionEngine()
    
    @pytest.fixture
    def cost_breakdown_data(self):
        """成本分解数据fixture"""
        return {
            ProviderType.OPENAI: CostBreakdown(
                provider=ProviderType.OPENAI,
                total_cost=Decimal("0.05"),
                total_requests=100,
                total_tokens=15000,
                avg_cost_per_request=Decimal("0.0005"),
                models_used=["gpt-4", "gpt-3.5-turbo"]
            ),
            ProviderType.ANTHROPIC: CostBreakdown(
                provider=ProviderType.ANTHROPIC,
                total_cost=Decimal("0.08"),
                total_requests=60,
                total_tokens=12000,
                avg_cost_per_request=Decimal("0.0013"),
                models_used=["claude-3-opus", "claude-3-sonnet"]
            ),
            ProviderType.GEMINI: CostBreakdown(
                provider=ProviderType.GEMINI,
                total_cost=Decimal("0.03"),
                total_requests=80,
                total_tokens=14000,
                avg_cost_per_request=Decimal("0.0004"),
                models_used=["gemini-pro"]
            )
        }
    
    def test_provider_switching_suggestions(self, suggestion_engine, cost_breakdown_data):
        """测试供应商切换建议"""
        suggestions = suggestion_engine.generate_provider_suggestions(cost_breakdown_data)
        
        # Should suggest switching from expensive Anthropic to cheaper Gemini
        switching_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.PROVIDER_SWITCH]
        assert len(switching_suggestions) > 0
        
        anthropic_suggestion = next(
            (s for s in switching_suggestions if "anthropic" in s.description.lower()), 
            None
        )
        assert anthropic_suggestion is not None
        assert anthropic_suggestion.potential_savings > 0
        assert "gemini" in anthropic_suggestion.recommendation.lower() or "openai" in anthropic_suggestion.recommendation.lower()
    
    def test_model_optimization_suggestions(self, suggestion_engine):
        """测试模型优化建议"""
        # High-cost model usage data
        model_usage = {
            "gpt-4": {
                "total_cost": Decimal("0.1"),
                "total_requests": 50,
                "avg_tokens": 500,
                "use_cases": ["complex_analysis", "creative_writing"]
            },
            "gpt-3.5-turbo": {
                "total_cost": Decimal("0.02"),
                "total_requests": 200,
                "avg_tokens": 200,
                "use_cases": ["simple_qa", "basic_chat"]
            }
        }
        
        suggestions = suggestion_engine.generate_model_suggestions(model_usage)
        
        model_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.MODEL_OPTIMIZATION]
        assert len(model_suggestions) > 0
        
        # Should suggest using cheaper models for simple tasks
        gpt4_suggestion = next(
            (s for s in model_suggestions if "gpt-4" in s.description.lower()),
            None
        )
        assert gpt4_suggestion is not None
        assert gpt4_suggestion.potential_savings > 0
    
    def test_usage_optimization_suggestions(self, suggestion_engine):
        """测试使用优化建议"""
        usage_patterns = [
            UsagePattern(
                pattern_type="high_token_usage",
                description="Sales agent using excessive tokens per request",
                impact_score=0.8,
                frequency=50,
                avg_cost=Decimal("0.005"),
                metadata={"agent_type": "sales", "avg_tokens": 1000}
            ),
            UsagePattern(
                pattern_type="redundant_requests",
                description="Multiple similar requests within short time",
                impact_score=0.6,
                frequency=30,
                avg_cost=Decimal("0.003"),
                metadata={"agent_type": "product", "similarity_threshold": 0.9}
            )
        ]
        
        suggestions = suggestion_engine.generate_usage_suggestions(usage_patterns)
        
        usage_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.USAGE_OPTIMIZATION]
        assert len(usage_suggestions) > 0
        
        # Should suggest token reduction for high usage
        token_suggestion = next(
            (s for s in usage_suggestions if "token" in s.description.lower()),
            None
        )
        assert token_suggestion is not None
        assert token_suggestion.potential_savings > 0
    
    def test_batch_processing_suggestions(self, suggestion_engine):
        """测试批处理建议"""
        # Pattern indicating many individual requests
        batch_opportunities = [
            {
                "agent_type": "product",
                "request_count": 100,
                "time_window": timedelta(hours=1),
                "similarity_score": 0.85,
                "potential_batch_size": 10,
                "current_cost": Decimal("0.05"),
                "batch_cost": Decimal("0.03")
            }
        ]
        
        suggestions = suggestion_engine.generate_batch_suggestions(batch_opportunities)
        
        batch_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.BATCH_PROCESSING]
        assert len(batch_suggestions) > 0
        
        batch_suggestion = batch_suggestions[0]
        assert batch_suggestion.potential_savings > 0
        assert "batch" in batch_suggestion.recommendation.lower()
    
    def test_caching_suggestions(self, suggestion_engine):
        """测试缓存建议"""
        # Repeated query patterns
        cache_opportunities = [
            {
                "query_pattern": "product recommendation for oily skin",
                "frequency": 50,
                "cache_hit_potential": 0.8,
                "current_cost": Decimal("0.025"),
                "cache_cost": Decimal("0.005"),
                "response_similarity": 0.9
            }
        ]
        
        suggestions = suggestion_engine.generate_cache_suggestions(cache_opportunities)
        
        cache_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.CACHING]
        assert len(cache_suggestions) > 0
        
        cache_suggestion = cache_suggestions[0]
        assert cache_suggestion.potential_savings > 0
        assert "cache" in cache_suggestion.recommendation.lower()
    
    def test_suggestion_prioritization(self, suggestion_engine, cost_breakdown_data):
        """测试建议优先级排序"""
        all_suggestions = []
        
        # Generate various suggestions
        all_suggestions.extend(suggestion_engine.generate_provider_suggestions(cost_breakdown_data))
        
        usage_patterns = [
            UsagePattern(
                pattern_type="high_cost_operations",
                description="Expensive operations detected",
                impact_score=0.9,
                frequency=20,
                avg_cost=Decimal("0.01")
            )
        ]
        all_suggestions.extend(suggestion_engine.generate_usage_suggestions(usage_patterns))
        
        # Prioritize suggestions
        prioritized = suggestion_engine.prioritize_suggestions(all_suggestions)
        
        assert len(prioritized) == len(all_suggestions)
        
        # Should be sorted by priority score (descending)
        for i in range(len(prioritized) - 1):
            assert prioritized[i].priority_score >= prioritized[i + 1].priority_score
        
        # High-impact suggestions should be first
        assert prioritized[0].priority_score > 0.5


class TestBudgetMonitor:
    """测试预算监控功能"""
    
    @pytest.fixture
    def budget_monitor(self):
        """预算监控器fixture"""
        thresholds = [
            BudgetThreshold(
                threshold_type="daily",
                limit=Decimal("1.0"),
                warning_percentage=0.8,
                critical_percentage=0.95
            ),
            BudgetThreshold(
                threshold_type="monthly",
                limit=Decimal("30.0"),
                warning_percentage=0.7,
                critical_percentage=0.9
            )
        ]
        return BudgetMonitor(thresholds=thresholds)
    
    def test_budget_threshold_monitoring(self, budget_monitor):
        """测试预算阈值监控"""
        # Test daily budget approaching warning
        daily_usage = Decimal("0.85")  # 85% of daily budget
        status = budget_monitor.check_budget_status(
            current_usage=daily_usage,
            threshold_type="daily"
        )
        
        assert status.status == "warning"
        assert status.usage_percentage >= 0.8
        assert status.remaining_budget == Decimal("0.15")
    
    def test_budget_alert_generation(self, budget_monitor):
        """测试预算告警生成"""
        # Exceed critical threshold
        critical_usage = Decimal("0.96")  # 96% of daily budget
        alerts = budget_monitor.generate_alerts(
            current_usage=critical_usage,
            threshold_type="daily",
            tenant_id="test_tenant"
        )
        
        assert len(alerts) > 0
        critical_alert = next(
            (a for a in alerts if a.alert_type == AlertType.CRITICAL),
            None
        )
        assert critical_alert is not None
        assert critical_alert.threshold_exceeded is True
    
    def test_projected_usage_calculation(self, budget_monitor):
        """测试预计使用量计算"""
        # Historical usage data
        historical_data = [
            {"date": datetime.now() - timedelta(days=i), "cost": Decimal("0.5")}
            for i in range(7, 0, -1)
        ]
        
        projection = budget_monitor.calculate_projected_usage(
            historical_data=historical_data,
            projection_period=timedelta(days=30)
        )
        
        assert projection["projected_monthly_cost"] > 0
        assert projection["projected_daily_average"] > 0
        assert "confidence_level" in projection
    
    def test_cost_anomaly_detection(self, budget_monitor):
        """测试成本异常检测"""
        # Normal usage pattern
        normal_costs = [Decimal("0.1") for _ in range(20)]
        
        # Add anomalous spike
        anomalous_costs = normal_costs + [Decimal("1.5")]
        
        anomalies = budget_monitor.detect_cost_anomalies(anomalous_costs)
        
        assert len(anomalies) > 0
        assert anomalies[-1]["is_anomaly"] is True
        assert anomalies[-1]["severity"] > 0.5
    
    def test_budget_recommendation_engine(self, budget_monitor):
        """测试预算建议引擎"""
        # Current spending pattern
        spending_data = {
            "current_monthly": Decimal("25.0"),
            "projected_monthly": Decimal("35.0"),
            "budget_limit": Decimal("30.0"),
            "growth_rate": 0.15
        }
        
        recommendations = budget_monitor.generate_budget_recommendations(spending_data)
        
        assert len(recommendations) > 0
        
        # Should recommend budget adjustment or cost reduction
        budget_rec = next(
            (r for r in recommendations if "budget" in r["type"].lower()),
            None
        )
        cost_rec = next(
            (r for r in recommendations if "cost" in r["type"].lower()),
            None
        )
        
        assert budget_rec is not None or cost_rec is not None


class TestBenchmarkDataManager:
    """测试基准数据管理器"""
    
    @pytest.fixture
    def benchmark_manager(self):
        """基准数据管理器fixture"""
        return BenchmarkDataManager()
    
    def test_industry_benchmark_comparison(self, benchmark_manager):
        """测试行业基准比较"""
        # Mock current usage
        current_metrics = {
            "cost_per_request": Decimal("0.005"),
            "tokens_per_request": 300,
            "requests_per_day": 1000,
            "monthly_cost": Decimal("150")
        }
        
        # Mock industry benchmarks
        benchmark_manager.industry_benchmarks = {
            "cosmetics": {
                "cost_per_request": Decimal("0.003"),
                "tokens_per_request": 250,
                "requests_per_day": 800,
                "monthly_cost": Decimal("100")
            }
        }
        
        comparison = benchmark_manager.compare_with_industry(
            current_metrics=current_metrics,
            industry="cosmetics"
        )
        
        assert "cost_efficiency" in comparison
        assert "token_efficiency" in comparison
        assert "usage_intensity" in comparison
        
        # Should indicate higher than average costs
        assert comparison["cost_efficiency"] < 1.0  # Above benchmark
        assert comparison["recommendations"] is not None
    
    def test_provider_benchmark_analysis(self, benchmark_manager):
        """测试供应商基准分析"""
        # Mock provider performance data
        provider_data = {
            ProviderType.OPENAI: {
                "avg_cost_per_token": Decimal("0.00002"),
                "avg_latency": 800,
                "success_rate": 0.98
            },
            ProviderType.ANTHROPIC: {
                "avg_cost_per_token": Decimal("0.00003"),
                "avg_latency": 600,
                "success_rate": 0.99
            },
            ProviderType.GEMINI: {
                "avg_cost_per_token": Decimal("0.00001"),
                "avg_latency": 700,
                "success_rate": 0.97
            }
        }
        
        analysis = benchmark_manager.analyze_provider_efficiency(provider_data)
        
        assert "cost_ranking" in analysis
        assert "performance_ranking" in analysis
        assert "value_ranking" in analysis
        
        # Gemini should rank high on cost efficiency
        assert analysis["cost_ranking"][0] == ProviderType.GEMINI
    
    def test_optimization_potential_calculation(self, benchmark_manager):
        """测试优化潜力计算"""
        current_usage = {
            "total_monthly_cost": Decimal("200"),
            "total_requests": 5000,
            "provider_distribution": {
                ProviderType.OPENAI: 0.6,
                ProviderType.ANTHROPIC: 0.4
            }
        }
        
        optimization_scenarios = benchmark_manager.calculate_optimization_potential(current_usage)
        
        assert len(optimization_scenarios) > 0
        
        # Should include cost reduction scenarios
        cost_scenarios = [s for s in optimization_scenarios if "cost" in s["optimization_type"]]
        assert len(cost_scenarios) > 0
        
        best_scenario = max(optimization_scenarios, key=lambda x: x["potential_savings"])
        assert best_scenario["potential_savings"] > 0


class TestIntegratedCostOptimization:
    """测试集成成本优化功能"""
    
    @pytest.fixture
    def full_cost_optimizer(self):
        """完整成本优化器fixture"""
        config = GlobalProviderConfig(
            providers={
                ProviderType.OPENAI: Mock(),
                ProviderType.ANTHROPIC: Mock(),
                ProviderType.GEMINI: Mock(),
                ProviderType.DEEPSEEK: Mock()
            },
            default_provider=ProviderType.OPENAI,
            tenant_id="cost_test"
        )
        
        return CostOptimizer(config)
    
    @pytest.mark.asyncio
    async def test_real_time_cost_tracking(self, full_cost_optimizer):
        """测试实时成本追踪"""
        # Mock LLM request and response
        request = LLMRequest(
            prompt="测试成本追踪",
            request_type=RequestType.CHAT,
            model="gpt-4"
        )
        
        response = LLMResponse(
            content="测试响应",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            cost=0.005,
            input_tokens=100,
            output_tokens=50,
            latency_ms=800
        )
        
        # Track cost
        await full_cost_optimizer.track_request_cost(
            request=request,
            response=response,
            tenant_id="test_tenant",
            agent_type="sales"
        )
        
        # Verify cost was recorded
        recent_costs = await full_cost_optimizer.get_recent_costs(
            tenant_id="test_tenant",
            time_window=timedelta(minutes=5)
        )
        
        assert len(recent_costs) == 1
        assert recent_costs[0].cost == Decimal("0.005")
        assert recent_costs[0].provider == ProviderType.OPENAI
    
    @pytest.mark.asyncio
    async def test_cost_optimization_workflow(self, full_cost_optimizer):
        """测试成本优化工作流"""
        # Generate sample cost data
        sample_records = []
        for i in range(50):
            record = CostRecord(
                provider=ProviderType.OPENAI if i % 2 == 0 else ProviderType.ANTHROPIC,
                model="gpt-4" if i % 2 == 0 else "claude-3-opus",
                input_tokens=150 + (i * 5),
                output_tokens=75 + (i * 2),
                cost=Decimal("0.005") if i % 2 == 0 else Decimal("0.008"),
                request_id=f"workflow_req_{i}",
                tenant_id="test_tenant",
                agent_type="sales",
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            sample_records.append(record)
        
        # Store records
        for record in sample_records:
            await full_cost_optimizer.store_cost_record(record)
        
        # Run optimization analysis
        optimization_result = await full_cost_optimizer.run_optimization_analysis(
            tenant_id="test_tenant",
            time_period=timedelta(hours=1)
        )
        
        assert "cost_breakdown" in optimization_result
        assert "suggestions" in optimization_result
        assert "potential_savings" in optimization_result
        
        # Should have suggestions
        assert len(optimization_result["suggestions"]) > 0
        assert optimization_result["potential_savings"] > 0
    
    def test_multi_tenant_cost_isolation(self, full_cost_optimizer):
        """测试多租户成本隔离"""
        tenant1_records = [
            CostRecord(
                provider=ProviderType.OPENAI,
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                cost=Decimal("0.003"),
                request_id=f"tenant1_req_{i}",
                tenant_id="tenant_1",
                agent_type="sales"
            ) for i in range(10)
        ]
        
        tenant2_records = [
            CostRecord(
                provider=ProviderType.ANTHROPIC,
                model="claude-3-sonnet",
                input_tokens=120,
                output_tokens=60,
                cost=Decimal("0.004"),
                request_id=f"tenant2_req_{i}",
                tenant_id="tenant_2",
                agent_type="product"
            ) for i in range(8)
        ]
        
        all_records = tenant1_records + tenant2_records
        
        # Analyze costs per tenant
        tenant1_analysis = full_cost_optimizer.analyze_tenant_costs(
            records=all_records,
            tenant_id="tenant_1"
        )
        
        tenant2_analysis = full_cost_optimizer.analyze_tenant_costs(
            records=all_records,
            tenant_id="tenant_2"
        )
        
        # Verify isolation
        assert tenant1_analysis["total_requests"] == 10
        assert tenant2_analysis["total_requests"] == 8
        assert tenant1_analysis["total_cost"] != tenant2_analysis["total_cost"]
        assert tenant1_analysis["primary_provider"] == ProviderType.OPENAI
        assert tenant2_analysis["primary_provider"] == ProviderType.ANTHROPIC


if __name__ == "__main__":
    # 运行基础成本优化测试
    async def run_basic_cost_tests():
        print("运行基础成本优化测试...")
        
        # 测试成本记录
        record = CostRecord(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost=Decimal("0.003"),
            request_id="test_req"
        )
        assert record.total_tokens == 150
        print(f"成本记录创建成功: {record.cost}")
        
        # 测试成本分析器
        analyzer = CostAnalyzer()
        records = [record]
        breakdown = analyzer.analyze_provider_costs(records, timedelta(days=1))
        assert ProviderType.OPENAI in breakdown
        print(f"成本分析器工作正常: {len(breakdown)} 个供应商")
        
        # 测试建议引擎
        suggestion_engine = SuggestionEngine()
        cost_data = {
            ProviderType.OPENAI: CostBreakdown(
                provider=ProviderType.OPENAI,
                total_cost=Decimal("0.1"),
                total_requests=100,
                total_tokens=1000,
                avg_cost_per_request=Decimal("0.001"),
                models_used=["gpt-4"]
            )
        }
        suggestions = suggestion_engine.generate_provider_suggestions(cost_data)
        print(f"建议引擎工作正常: {len(suggestions)} 个建议")
        
        # 测试预算监控
        thresholds = [
            BudgetThreshold(
                threshold_type="daily",
                limit=Decimal("1.0"),
                warning_percentage=0.8
            )
        ]
        budget_monitor = BudgetMonitor(thresholds)
        status = budget_monitor.check_budget_status(Decimal("0.5"), "daily")
        assert status.status == "normal"
        print(f"预算监控工作正常: {status.status}")
        
        print("基础成本优化测试完成!")
    
    asyncio.run(run_basic_cost_tests())