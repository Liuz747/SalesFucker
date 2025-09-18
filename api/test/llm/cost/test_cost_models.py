"""
成本优化模型测试套件

该测试模块专注于成本优化相关数据模型的测试:
- 成本记录模型验证
- 使用指标模型测试
- 成本分解结构测试
- 预算状态模型测试
"""

import pytest

@pytest.mark.skip(reason="Feature removed in simplified LLM system")
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import json

from core.llm.cost_optimizer.models import (
    CostRecord, UsageMetrics, CostBreakdown, 
    OptimizationOpportunity, BudgetStatus
)
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType


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
        assert record.total_tokens == 150
        assert record.cost_per_token == Decimal("0.003") / 150
    
    def test_cost_record_validation(self):
        """测试成本记录验证"""
        # Test negative values are handled correctly
        with pytest.raises(ValueError):
            CostRecord(
                provider=ProviderType.OPENAI,
                model="gpt-4",
                input_tokens=-10,  # Negative tokens should be invalid
                output_tokens=50,
                cost=Decimal("0.003"),
                request_id="req_123",
                tenant_id="tenant_test"
            )
        
        # Test zero cost is allowed
        record = CostRecord(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=0,
            output_tokens=0,
            cost=Decimal("0.000"),
            request_id="req_123",
            tenant_id="tenant_test"
        )
        assert record.cost == Decimal("0.000")
    
    def test_cost_record_serialization(self):
        """测试成本记录序列化"""
        record = CostRecord(
            provider=ProviderType.ANTHROPIC,
            model="claude-3-sonnet",
            input_tokens=200,
            output_tokens=100,
            cost=Decimal("0.006"),
            request_id="req_456",
            tenant_id="tenant_test",
            agent_type="compliance"
        )
        
        # Test to_dict
        record_dict = record.to_dict()
        assert record_dict["provider"] == "anthropic"
        assert record_dict["model"] == "claude-3-sonnet"
        assert record_dict["total_tokens"] == 300
        
        # Test from_dict
        restored_record = CostRecord.from_dict(record_dict)
        assert restored_record.provider == ProviderType.ANTHROPIC
        assert restored_record.cost == Decimal("0.006")


class TestUsageMetrics:
    """测试使用指标模型"""
    
    def test_usage_metrics_creation(self):
        """测试使用指标创建"""
        metrics = UsageMetrics(
            total_requests=1000,
            total_tokens=150000,
            total_cost=Decimal("45.75"),
            avg_tokens_per_request=150.0,
            avg_cost_per_request=Decimal("0.04575"),
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now()
        )
        
        assert metrics.total_requests == 1000
        assert metrics.total_tokens == 150000
        assert metrics.total_cost == Decimal("45.75")
        assert metrics.avg_tokens_per_request == 150.0
        assert metrics.avg_cost_per_request == Decimal("0.04575")
    
    def test_usage_metrics_calculations(self):
        """测试使用指标计算"""
        metrics = UsageMetrics(
            total_requests=500,
            total_tokens=75000,
            total_cost=Decimal("22.50")
        )
        
        # Test calculated properties
        assert metrics.cost_per_token == Decimal("22.50") / 75000
        assert metrics.tokens_per_request == 75000 / 500
        
        # Test cost efficiency rating
        efficiency = metrics.calculate_efficiency_score()
        assert 0 <= efficiency <= 1
    
    def test_usage_metrics_comparison(self):
        """测试使用指标比较"""
        metrics1 = UsageMetrics(
            total_requests=1000,
            total_tokens=150000,
            total_cost=Decimal("45.00")
        )
        
        metrics2 = UsageMetrics(
            total_requests=800,
            total_tokens=120000,
            total_cost=Decimal("40.00")
        )
        
        # Compare efficiency
        comparison = metrics1.compare_with(metrics2)
        assert "cost_difference" in comparison
        assert "efficiency_change" in comparison


class TestCostBreakdown:
    """测试成本分解模型"""
    
    def test_cost_breakdown_creation(self):
        """测试成本分解创建"""
        breakdown = CostBreakdown(
            by_provider={
                ProviderType.OPENAI: Decimal("25.50"),
                ProviderType.ANTHROPIC: Decimal("15.75"),
                ProviderType.GEMINI: Decimal("8.25")
            },
            by_agent={
                "sales": Decimal("20.00"),
                "compliance": Decimal("15.50"),
                "sentiment": Decimal("14.00")
            },
            by_model={
                "gpt-4": Decimal("30.00"),
                "claude-3-sonnet": Decimal("12.50"),
                "gemini-pro": Decimal("7.00")
            },
            total_cost=Decimal("49.50")
        )
        
        assert len(breakdown.by_provider) == 3
        assert len(breakdown.by_agent) == 3
        assert len(breakdown.by_model) == 3
        assert breakdown.total_cost == Decimal("49.50")
    
    def test_cost_breakdown_percentages(self):
        """测试成本分解百分比计算"""
        breakdown = CostBreakdown(
            by_provider={
                ProviderType.OPENAI: Decimal("30.00"),
                ProviderType.ANTHROPIC: Decimal("20.00")
            },
            total_cost=Decimal("50.00")
        )
        
        percentages = breakdown.get_provider_percentages()
        assert percentages[ProviderType.OPENAI] == 0.6  # 60%
        assert percentages[ProviderType.ANTHROPIC] == 0.4  # 40%
    
    def test_cost_breakdown_top_contributors(self):
        """测试成本分解主要贡献者"""
        breakdown = CostBreakdown(
            by_agent={
                "sales": Decimal("25.00"),
                "compliance": Decimal("15.00"),
                "sentiment": Decimal("8.00"),
                "product": Decimal("2.00")
            },
            total_cost=Decimal("50.00")
        )
        
        top_agents = breakdown.get_top_agents(limit=2)
        assert len(top_agents) == 2
        assert top_agents[0][0] == "sales"  # Top contributor
        assert top_agents[0][1] == Decimal("25.00")


class TestOptimizationOpportunity:
    """测试优化机会模型"""
    
    def test_optimization_opportunity_creation(self):
        """测试优化机会创建"""
        opportunity = OptimizationOpportunity(
            opportunity_id="opt_001",
            opportunity_type="provider_switching",
            description="Switch from OpenAI to DeepSeek for basic tasks",
            potential_savings=Decimal("15.75"),
            implementation_effort="low",
            confidence_score=0.85,
            affected_agents=["sales", "product"],
            estimated_impact={
                "monthly_savings": 15.75,
                "performance_impact": "minimal"
            }
        )
        
        assert opportunity.opportunity_id == "opt_001"
        assert opportunity.opportunity_type == "provider_switching"
        assert opportunity.potential_savings == Decimal("15.75")
        assert opportunity.confidence_score == 0.85
        assert len(opportunity.affected_agents) == 2
    
    def test_optimization_opportunity_priority(self):
        """测试优化机会优先级"""
        high_priority = OptimizationOpportunity(
            opportunity_id="opt_high",
            opportunity_type="prompt_optimization",
            potential_savings=Decimal("50.00"),
            implementation_effort="low",
            confidence_score=0.95
        )
        
        low_priority = OptimizationOpportunity(
            opportunity_id="opt_low",
            opportunity_type="model_switching",
            potential_savings=Decimal("5.00"),
            implementation_effort="high",
            confidence_score=0.60
        )
        
        assert high_priority.calculate_priority_score() > low_priority.calculate_priority_score()


class TestBudgetStatus:
    """测试预算状态模型"""
    
    def test_budget_status_creation(self):
        """测试预算状态创建"""
        status = BudgetStatus(
            tenant_id="tenant_budget",
            period="monthly",
            budget_limit=Decimal("500.00"),
            current_spend=Decimal("275.50"),
            projected_spend=Decimal("420.00"),
            days_remaining=15,
            alert_thresholds=[0.8, 0.9, 1.0]
        )
        
        assert status.tenant_id == "tenant_budget"
        assert status.budget_limit == Decimal("500.00")
        assert status.current_spend == Decimal("275.50")
        assert status.utilization_percentage == 0.551  # 55.1%
        assert status.remaining_budget == Decimal("224.50")
    
    def test_budget_status_alert_levels(self):
        """测试预算状态警报级别"""
        # Test warning level (80% utilization)
        warning_status = BudgetStatus(
            tenant_id="tenant_warning",
            budget_limit=Decimal("100.00"),
            current_spend=Decimal("85.00")
        )
        
        assert warning_status.get_alert_level() == "warning"
        
        # Test critical level (95% utilization)
        critical_status = BudgetStatus(
            tenant_id="tenant_critical",
            budget_limit=Decimal("100.00"),
            current_spend=Decimal("95.00")
        )
        
        assert critical_status.get_alert_level() == "critical"
    
    def test_budget_status_projections(self):
        """测试预算状态预测"""
        status = BudgetStatus(
            tenant_id="tenant_projection",
            budget_limit=Decimal("1000.00"),
            current_spend=Decimal("300.00"),
            days_elapsed=10,
            days_remaining=20
        )
        
        projected = status.calculate_projected_spend()
        # Should project based on current spending rate
        assert projected > status.current_spend
        
        # Test if projection exceeds budget
        assert status.will_exceed_budget() in [True, False]


if __name__ == "__main__":
    # 运行成本模型测试
    def run_cost_model_tests():
        print("运行成本模型测试...")
        
        # 测试成本记录
        record = CostRecord(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost=Decimal("0.003"),
            request_id="test_req",
            tenant_id="test_tenant"
        )
        assert record.total_tokens == 150
        print(f"成本记录创建成功: {record.cost}")
        
        # 测试使用指标
        metrics = UsageMetrics(
            total_requests=100,
            total_tokens=15000,
            total_cost=Decimal("4.50")
        )
        assert metrics.tokens_per_request == 150
        print(f"使用指标创建成功: {metrics.avg_cost_per_request}")
        
        print("成本模型测试完成!")
    
    run_cost_model_tests()