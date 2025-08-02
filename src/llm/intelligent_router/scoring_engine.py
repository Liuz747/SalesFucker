"""
评分引擎模块

负责计算供应商评分的核心逻辑。
"""

from typing import List, Dict, Any
from ..base_provider import BaseProvider, LLMRequest
from ..provider_config import ModelCapability, ProviderType
from .models import RoutingContext, ProviderScore, RoutingStrategy


class ScoringEngine:
    """评分引擎类"""
    
    def __init__(self):
        """初始化评分引擎"""
        self.agent_optimizations = {
            "compliance": {
                "preferred_capabilities": [ModelCapability.REASONING],
                "min_quality": 0.9,
                "cost_sensitivity": 0.3
            },
            "sentiment": {
                "preferred_capabilities": [ModelCapability.CHINESE_OPTIMIZATION],
                "min_quality": 0.85,
                "cost_sensitivity": 0.4
            },
            "intent": {
                "preferred_capabilities": [ModelCapability.FAST_RESPONSE],
                "min_quality": 0.8,
                "cost_sensitivity": 0.6
            },
            "sales": {
                "preferred_capabilities": [ModelCapability.REASONING, ModelCapability.CHINESE_OPTIMIZATION],
                "min_quality": 0.85,
                "cost_sensitivity": 0.4
            },
            "product": {
                "preferred_capabilities": [ModelCapability.REASONING],
                "min_quality": 0.9,
                "cost_sensitivity": 0.3
            },
            "memory": {
                "preferred_capabilities": [ModelCapability.FAST_RESPONSE],
                "min_quality": 0.7,
                "cost_sensitivity": 0.8
            },
            "suggestion": {
                "preferred_capabilities": [ModelCapability.REASONING],
                "min_quality": 0.85,
                "cost_sensitivity": 0.5
            }
        }
    
    async def score_providers(
        self,
        providers: List[BaseProvider],
        request: LLMRequest,
        context: RoutingContext,
        strategy: RoutingStrategy,
        learning_engine
    ) -> List[ProviderScore]:
        """为供应商计算综合评分"""
        provider_scores = []
        
        for provider in providers:
            # 计算各维度得分
            performance_score = await self._calculate_performance_score(
                provider, context, learning_engine
            )
            cost_score = await self._calculate_cost_score(provider, request, context)
            capability_score = await self._calculate_capability_score(provider, request, context)
            health_score = self._calculate_health_score(provider)
            load_score = self._calculate_load_score(provider)
            
            # 根据策略计算权重
            weights = self._get_strategy_weights(strategy, context)
            
            # 计算总分
            total_score = (
                performance_score * weights["performance"] +
                cost_score * weights["cost"] +
                capability_score * weights["capability"] +
                health_score * weights["health"] +
                load_score * weights["load"]
            )
            
            # 应用智能体特定的调整
            total_score = self._apply_agent_adjustments(total_score, provider, context)
            
            provider_score = ProviderScore(
                provider=provider,
                total_score=total_score,
                performance_score=performance_score,
                cost_score=cost_score,
                capability_score=capability_score,
                health_score=health_score,
                load_score=load_score,
                details={
                    "strategy": strategy,
                    "weights": weights,
                    "agent_type": context.agent_type
                }
            )
            
            provider_scores.append(provider_score)
        
        # 按总分排序
        provider_scores.sort(key=lambda x: x.total_score, reverse=True)
        return provider_scores
    
    async def _calculate_performance_score(
        self, 
        provider: BaseProvider, 
        context: RoutingContext,
        learning_engine
    ) -> float:
        """计算性能得分"""
        base_score = provider.health.status_score
        
        # 历史性能调整
        provider_key = f"{provider.provider_type}_{context.tenant_id or 'default'}"
        performance_data = learning_engine.get_provider_performance(provider_key)
        
        if performance_data:
            success_rate = performance_data.get("success_rate", 0.95)
            base_score *= success_rate
            
            avg_response_time = performance_data.get("avg_response_time", 1.0)
            if avg_response_time > 2.0:
                base_score *= max(0.5, 2.0 / avg_response_time)
        
        # 智能体类型历史表现
        agent_key = f"{context.agent_type}_{provider.provider_type}"
        agent_preferences = learning_engine.get_agent_preferences(agent_key)
        
        if agent_preferences:
            agent_score = agent_preferences.get("performance", 1.0)
            base_score *= agent_score
        
        return min(1.0, max(0.0, base_score))
    
    async def _calculate_cost_score(
        self, 
        provider: BaseProvider, 
        request: LLMRequest,
        context: RoutingContext
    ) -> float:
        """计算成本得分(成本越低得分越高)"""
        available_models = await provider.get_available_models()
        
        selected_model = None
        for model in available_models:
            if not request.model or model.model_name == request.model:
                selected_model = model
                break
        
        if not selected_model and available_models:
            selected_model = available_models[0]
        
        if not selected_model:
            return 0.5
        
        estimated_tokens = request.max_tokens or 1000
        estimated_cost = (estimated_tokens / 1000) * selected_model.cost_per_1k_tokens
        
        max_cost = 0.1
        cost_score = max(0.0, 1.0 - (estimated_cost / max_cost))
        
        if context.cost_priority < 0.5:
            cost_score = cost_score ** 0.5
        
        return cost_score
    
    async def _calculate_capability_score(
        self, 
        provider: BaseProvider, 
        request: LLMRequest,
        context: RoutingContext
    ) -> float:
        """计算能力匹配得分"""
        available_models = await provider.get_available_models()
        if not available_models:
            return 0.3
        
        capability_score = 0.5
        
        if context.agent_type in self.agent_optimizations:
            agent_config = self.agent_optimizations[context.agent_type]
            preferred_capabilities = agent_config["preferred_capabilities"]
            
            for model in available_models:
                capability_matches = len(
                    set(preferred_capabilities) & set(model.capabilities)
                )
                if capability_matches > 0:
                    capability_score += capability_matches * 0.2
        
        # 中文内容特殊处理
        if context.content_language == "zh":
            for model in available_models:
                if ModelCapability.CHINESE_OPTIMIZATION in model.capabilities:
                    capability_score += 0.3
                if model.supports_chinese:
                    capability_score += 0.2
        
        # 多模态需求
        if context.has_multimodal:
            for model in available_models:
                if ModelCapability.MULTIMODAL in model.capabilities:
                    capability_score += 0.4
                    break
            else:
                capability_score -= 0.5
        
        # 紧急程度处理
        if context.urgency_level == "high":
            for model in available_models:
                if ModelCapability.FAST_RESPONSE in model.capabilities:
                    capability_score += 0.3
                    break
        
        return min(1.0, max(0.0, capability_score))
    
    def _calculate_health_score(self, provider: BaseProvider) -> float:
        """计算健康状态得分"""
        health = provider.health
        
        if not health.is_healthy:
            return 0.1
        
        score = 1.0
        
        if health.error_rate > 0.05:
            score *= (1.0 - min(health.error_rate, 0.5))
        
        if health.consecutive_failures > 0:
            score *= max(0.3, 1.0 - (health.consecutive_failures * 0.1))
        
        if health.avg_response_time > 3000:
            score *= max(0.5, 3000 / health.avg_response_time)
        
        return score
    
    def _calculate_load_score(self, provider: BaseProvider) -> float:
        """计算负载得分"""
        remaining_rate = provider.health.rate_limit_remaining
        max_rate = provider.config.rate_limit_rpm
        
        if max_rate <= 0:
            return 1.0
        
        load_ratio = remaining_rate / max_rate
        
        if load_ratio > 0.8:
            return 1.0
        elif load_ratio > 0.5:
            return 0.8
        elif load_ratio > 0.2:
            return 0.6
        else:
            return 0.3
    
    def _get_strategy_weights(
        self, 
        strategy: RoutingStrategy, 
        context: RoutingContext
    ) -> Dict[str, float]:
        """根据策略获取各维度权重"""
        if strategy == RoutingStrategy.PERFORMANCE_FIRST:
            return {
                "performance": 0.4,
                "cost": 0.1,
                "capability": 0.3,
                "health": 0.15,
                "load": 0.05
            }
        elif strategy == RoutingStrategy.COST_FIRST:
            return {
                "performance": 0.2,
                "cost": 0.45,
                "capability": 0.2,
                "health": 0.1,
                "load": 0.05
            }
        elif strategy == RoutingStrategy.BALANCED:
            return {
                "performance": 0.25,
                "cost": 0.25,
                "capability": 0.25,
                "health": 0.15,
                "load": 0.1
            }
        elif strategy == RoutingStrategy.AGENT_OPTIMIZED:
            if context.agent_type in self.agent_optimizations:
                agent_config = self.agent_optimizations[context.agent_type]
                cost_sensitivity = agent_config["cost_sensitivity"]
                return {
                    "performance": 0.3,
                    "cost": cost_sensitivity * 0.4,
                    "capability": 0.35,
                    "health": 0.1,
                    "load": 0.05
                }
            return self._get_strategy_weights(RoutingStrategy.BALANCED, context)
        elif strategy == RoutingStrategy.CHINESE_OPTIMIZED:
            return {
                "performance": 0.2,
                "cost": 0.2,
                "capability": 0.4,
                "health": 0.15,
                "load": 0.05
            }
        else:
            return self._get_strategy_weights(RoutingStrategy.BALANCED, context)
    
    def _apply_agent_adjustments(
        self, 
        base_score: float, 
        provider: BaseProvider, 
        context: RoutingContext
    ) -> float:
        """应用智能体特定的评分调整"""
        if not context.agent_type:
            return base_score
        
        # 特定供应商-智能体组合的调整
        adjustments = {
            ("compliance", ProviderType.ANTHROPIC): 1.1,
            ("sentiment", ProviderType.GEMINI): 1.05,
            ("intent", ProviderType.OPENAI): 1.05,
            ("sales", ProviderType.ANTHROPIC): 1.1,
            ("product", ProviderType.OPENAI): 1.05,
        }
        
        adjustment_key = (context.agent_type, provider.provider_type)
        adjustment_factor = adjustments.get(adjustment_key, 1.0)
        
        return base_score * adjustment_factor
    
    def get_agent_optimizations(self) -> Dict[str, Any]:
        """获取智能体优化配置"""
        return self.agent_optimizations.copy()