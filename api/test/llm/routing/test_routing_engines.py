"""
路由引擎详细测试套件

该测试套件专门测试路由系统的核心引擎组件:
- 评分引擎 (ScoringEngine)
- 规则引擎 (RuleEngine)
- 选择引擎 (SelectionEngine)
"""

import pytest

@pytest.mark.skip(reason="Feature removed in simplified LLM system")
from unittest.mock import Mock
from datetime import datetime

from core.llm.intelligent_router.rule_engine import RuleEngine, RoutingRule
from core.llm.intelligent_router.scoring_engine import ScoringEngine, ScoringCriteria
from core.llm.intelligent_router.selection_engine import SelectionEngine
# Note: Intelligent routing simplified in new system
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.providers.base import BaseProvider


class TestScoringEngine:
    """测试供应商评分引擎"""
    
    @pytest.fixture
    def scoring_engine(self):
        """评分引擎fixture"""
        return ScoringEngine()
    
    def test_performance_scoring(self, scoring_engine):
        """测试性能评分算法"""
        health_data = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=800,
                success_rate=0.98,
                error_rate=0.02
            ),
            ProviderType.ANTHROPIC: ProviderHealth(
                provider=ProviderType.ANTHROPIC,
                status="healthy",
                latency_ms=600,  # Faster
                success_rate=0.99,  # Better
                error_rate=0.01
            )
        }
        
        criteria = ScoringCriteria(
            performance_weight=1.0,
            cost_weight=0.0,
            reliability_weight=0.0
        )
        
        scores = scoring_engine.calculate_scores(health_data, {}, criteria)
        
        # Anthropic should score higher
        assert scores[ProviderType.ANTHROPIC].total_score > scores[ProviderType.OPENAI].total_score
        assert scores[ProviderType.ANTHROPIC].performance_score > scores[ProviderType.OPENAI].performance_score
    
    def test_cost_scoring(self, scoring_engine):
        """测试成本评分算法"""
        cost_data = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.DEEPSEEK: {"cost_per_1k_tokens": 0.0005}  # Cheaper
        }
        
        criteria = ScoringCriteria(
            performance_weight=0.0,
            cost_weight=1.0,
            reliability_weight=0.0
        )
        
        scores = scoring_engine.calculate_scores({}, cost_data, criteria)
        
        # DeepSeek should score higher (lower cost)
        assert scores[ProviderType.DEEPSEEK].total_score > scores[ProviderType.OPENAI].total_score
        assert scores[ProviderType.DEEPSEEK].cost_score > scores[ProviderType.OPENAI].cost_score
    
    def test_weighted_scoring(self, scoring_engine):
        """测试加权评分算法"""
        health_data = {
            ProviderType.OPENAI: ProviderHealth(
                provider=ProviderType.OPENAI,
                status="healthy",
                latency_ms=1000,  # Slower
                success_rate=0.98,  # More reliable
                error_rate=0.02
            ),
            ProviderType.GEMINI: ProviderHealth(
                provider=ProviderType.GEMINI,
                status="healthy",
                latency_ms=600,   # Faster
                success_rate=0.95,  # Less reliable
                error_rate=0.05
            )
        }
        
        cost_data = {
            ProviderType.OPENAI: {"cost_per_1k_tokens": 0.002},
            ProviderType.GEMINI: {"cost_per_1k_tokens": 0.001}  # Cheaper
        }
        
        criteria = ScoringCriteria(
            performance_weight=0.4,
            cost_weight=0.4, 
            reliability_weight=0.2
        )
        
        scores = scoring_engine.calculate_scores(health_data, cost_data, criteria)
        
        # Verify weighted calculation
        openai_score = scores[ProviderType.OPENAI]
        gemini_score = scores[ProviderType.GEMINI]
        
        # Gemini wins on performance and cost, loses on reliability
        assert gemini_score.performance_score > openai_score.performance_score
        assert gemini_score.cost_score > openai_score.cost_score
        assert openai_score.reliability_score > gemini_score.reliability_score


class TestRuleEngine:
    """测试路由规则引擎"""
    
    @pytest.fixture
    def rule_engine(self):
        """规则引擎fixture"""
        return RuleEngine()
    
    def test_language_based_rules(self, rule_engine):
        """测试基于语言的路由规则"""
        chinese_rule = RoutingRule(
            rule_id="chinese_content",
            condition={"language": "chinese"},
            action={"preferred_providers": [ProviderType.DEEPSEEK]},
            priority=10
        )
        rule_engine.add_rule(chinese_rule)
        
        context = RoutingContext(
            content_language="chinese",
            agent_type="product"
        )
        
        request = LLMRequest(
            prompt="推荐中文化妆品",
            request_type=RequestType.CHAT,
            metadata={"language": "chinese"}
        )
        
        applicable_rules = rule_engine.get_applicable_rules(request, context)
        assert len(applicable_rules) == 1
        assert applicable_rules[0].rule_id == "chinese_content"
    
    def test_agent_specific_rules(self, rule_engine):
        """测试智能体特定规则"""
        compliance_rule = RoutingRule(
            rule_id="compliance_accuracy",
            condition={"agent_type": "compliance"},
            action={"preferred_providers": [ProviderType.ANTHROPIC]},
            priority=8
        )
        rule_engine.add_rule(compliance_rule)
        
        context = RoutingContext(agent_type="compliance")
        request = LLMRequest(prompt="Check compliance", request_type=RequestType.CHAT)
        
        rules = rule_engine.get_applicable_rules(request, context)
        assert len(rules) == 1
        assert rules[0].rule_id == "compliance_accuracy"
    
    def test_priority_ordering(self, rule_engine):
        """测试优先级排序"""
        high_rule = RoutingRule(
            rule_id="high_priority",
            condition={"agent_type": "sales"},
            action={"preferred_providers": [ProviderType.OPENAI]},
            priority=10
        )
        
        low_rule = RoutingRule(
            rule_id="low_priority", 
            condition={"agent_type": "sales"},
            action={"preferred_providers": [ProviderType.GEMINI]},
            priority=5
        )
        
        rule_engine.add_rule(low_rule)  # Add lower first
        rule_engine.add_rule(high_rule)  # Add higher second
        
        context = RoutingContext(agent_type="sales")
        request = LLMRequest(prompt="Sales prompt", request_type=RequestType.CHAT)
        
        rules = rule_engine.get_applicable_rules(request, context)
        
        # Should be sorted by priority
        assert len(rules) == 2
        assert rules[0].rule_id == "high_priority"
        assert rules[1].rule_id == "low_priority"


class TestSelectionEngine:
    """测试供应商选择引擎"""
    
    @pytest.fixture
    def selection_engine(self):
        """选择引擎fixture"""
        scoring_engine = Mock(spec=ScoringEngine)
        rule_engine = Mock(spec=RuleEngine)
        learning_engine = Mock()
        return SelectionEngine(scoring_engine, rule_engine, learning_engine)
    
    def test_rule_based_selection(self, selection_engine):
        """测试基于规则的选择"""
        mock_rule = RoutingRule(
            rule_id="test_rule",
            condition={"agent_type": "compliance"},
            action={"preferred_providers": [ProviderType.ANTHROPIC]},
            priority=10
        )
        selection_engine.rule_engine.get_applicable_rules.return_value = [mock_rule]
        
        context = RoutingContext(agent_type="compliance")
        request = LLMRequest(prompt="Test", request_type=RequestType.CHAT)
        available_providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        
        decision = selection_engine.select_provider(request, context, available_providers)
        
        assert decision.selected_provider == ProviderType.ANTHROPIC
        assert decision.decision_reason == "rule_based"
        assert mock_rule.rule_id in decision.applied_rules
    
    def test_score_based_selection(self, selection_engine):
        """测试基于评分的选择"""
        # No applicable rules
        selection_engine.rule_engine.get_applicable_rules.return_value = []
        
        # Mock scoring results
        mock_scores = {
            ProviderType.OPENAI: ProviderScore(
                provider=ProviderType.OPENAI,
                total_score=0.85,
                performance_score=0.8,
                cost_score=0.7,
                reliability_score=0.9
            ),
            ProviderType.ANTHROPIC: ProviderScore(
                provider=ProviderType.ANTHROPIC,
                total_score=0.92,  # Higher score
                performance_score=0.95,
                cost_score=0.6,
                reliability_score=0.95
            )
        }
        selection_engine.scoring_engine.calculate_scores.return_value = mock_scores
        
        context = RoutingContext(agent_type="sales")
        request = LLMRequest(prompt="Test", request_type=RequestType.CHAT)
        available_providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        
        decision = selection_engine.select_provider(request, context, available_providers)
        
        assert decision.selected_provider == ProviderType.ANTHROPIC
        assert decision.decision_reason == "score_based"
        assert decision.provider_score.total_score == 0.92
    
    def test_fallback_selection(self, selection_engine):
        """测试回退选择机制"""
        # No rules, no scores, no learning
        selection_engine.rule_engine.get_applicable_rules.return_value = []
        selection_engine.scoring_engine.calculate_scores.return_value = {}
        selection_engine.learning_engine.get_context_recommendations.return_value = None
        
        context = RoutingContext(agent_type="unknown")
        request = LLMRequest(prompt="Test", request_type=RequestType.CHAT)
        available_providers = [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        
        decision = selection_engine.select_provider(request, context, available_providers)
        
        # Should fallback to first available
        assert decision.selected_provider in available_providers
        assert decision.decision_reason == "fallback"


if __name__ == "__main__":
    print("路由引擎测试模块加载成功")
    print("测试覆盖: 评分引擎、规则引擎、选择引擎")