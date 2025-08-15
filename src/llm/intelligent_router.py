"""
智能路由器模块

该模块实现了多LLM供应商的智能路由系统，负责根据多种因素动态选择
最优的供应商处理特定请求，包括失败重试和上下文保持功能。

核心功能:
- 基于规则和机器学习的供应商选择
- 成本优化路由算法
- 实时性能分析和适应性调整
- 智能体类型特化路由
- 中文内容优化路由
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import random

from .base_provider import BaseProvider, LLMRequest, LLMResponse, ProviderError
from .provider_config import (
    ProviderType, 
    AgentProviderMapping, 
    RoutingRule,
    ModelCapability,
    ProviderHealth
)
from .provider_manager import ProviderManager
from utils import get_component_logger, ErrorHandler


# Integrated models (from intelligent_router_modules/models.py)
class RoutingStrategy(str, Enum):
    """路由策略枚举"""
    PERFORMANCE_FIRST = "performance_first"  # 性能优先
    COST_FIRST = "cost_first"               # 成本优先
    BALANCED = "balanced"                   # 平衡策略
    AGENT_OPTIMIZED = "agent_optimized"     # 智能体优化
    CHINESE_OPTIMIZED = "chinese_optimized" # 中文优化


@dataclass
class RoutingContext:
    """路由上下文数据"""
    agent_type: Optional[str] = None
    tenant_id: Optional[str] = None
    conversation_id: Optional[str] = None
    content_language: Optional[str] = None
    has_multimodal: bool = False
    urgency_level: str = "medium"  # low/medium/high
    cost_priority: float = 0.5     # 0=最低成本, 1=不考虑成本
    quality_threshold: float = 0.8
    previous_provider: Optional[ProviderType] = None
    retry_count: int = 0


@dataclass
class ProviderScore:
    """供应商评分"""
    provider: BaseProvider
    total_score: float
    performance_score: float
    cost_score: float
    capability_score: float
    health_score: float
    load_score: float
    details: Dict[str, Any]


class IntelligentRouter:
    """
    智能路由器类
    
    实现多供应商的智能选择、负载均衡和故障转移功能。
    使用多因素评分算法选择最优供应商。
    """
    
    def __init__(self, provider_manager: ProviderManager):
        """
        初始化智能路由器
        
        参数:
            provider_manager: 供应商管理器实例
        """
        self.provider_manager = provider_manager
        self.logger = get_component_logger(__name__, "IntelligentRouter")
        self.error_handler = ErrorHandler("intelligent_router")
        
        # 集成的引擎功能 (不再需要单独的引擎类)
        
        # 路由历史和学习数据
        self.routing_history: List[Dict[str, Any]] = []
        self.provider_performance: Dict[str, Dict[str, float]] = {}
        self.agent_preferences: Dict[str, Dict[str, float]] = {}
        
        # 路由配置
        self.default_strategy = RoutingStrategy.BALANCED
        self.max_routing_history = 10000
        self.learning_window = timedelta(hours=24)
        
        # 智能体优化配置
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
        
        self.logger.info("智能路由器初始化完成")
    
    async def route_request(
        self, 
        request: LLMRequest, 
        context: RoutingContext,
        strategy: Optional[RoutingStrategy] = None
    ) -> BaseProvider:
        """
        为请求路由到最优供应商
        
        参数:
            request: LLM请求对象
            context: 路由上下文
            strategy: 路由策略，可选
            
        返回:
            BaseProvider: 选中的供应商实例
            
        异常:
            ProviderError: 无可用供应商时抛出
        """
        start_time = time.time()
        strategy = strategy or self.default_strategy
        
        try:
            # 获取可用供应商
            available_providers = self.provider_manager.get_available_providers(context.tenant_id)
            
            if not available_providers:
                raise ProviderError(
                    "没有可用的供应商", 
                    None, 
                    "NO_AVAILABLE_PROVIDERS"
                )
            
            # 应用路由规则过滤 (集成功能)
            filtered_providers = self._apply_routing_rules(
                available_providers, request, context
            )
            
            if not filtered_providers:
                # 如果规则过滤后没有可用供应商，回退到所有可用供应商
                filtered_providers = available_providers
                self.logger.warning("路由规则过滤后无可用供应商，回退到全部供应商")
            
            # 计算供应商评分 (集成功能)
            provider_scores = self._score_providers(
                filtered_providers, request, context, strategy
            )
            
            # 选择最优供应商 (集成功能)
            selected_provider = self._select_provider(provider_scores, context)
            
            # 记录路由决策 (集成功能)
            routing_time = time.time() - start_time
            self._record_routing_decision(
                request, context, selected_provider, provider_scores, routing_time
            )
            
            self.logger.info(
                f"路由完成: {selected_provider.provider_type}, "
                f"智能体: {context.agent_type}, "
                f"策略: {strategy}, "
                f"耗时: {routing_time:.3f}s"
            )
            
            return selected_provider
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "request_id": request.request_id,
                "agent_type": context.agent_type,
                "tenant_id": context.tenant_id,
                "strategy": strategy
            })
            raise
    
    async def update_performance_metrics(
        self,
        request_id: str,
        provider_type: ProviderType,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None
    ):
        """更新供应商性能指标"""
        self._update_performance_metrics(
            request_id, provider_type, success, response_time, error_type
        )
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return self._get_routing_stats()
    
    def get_agent_optimizations(self) -> Dict[str, Any]:
        """获取智能体优化配置"""
        return self.agent_optimizations
    
    # 集成的引擎功能实现
    def _apply_routing_rules(
        self, 
        providers: List[BaseProvider], 
        request: LLMRequest, 
        context: RoutingContext
    ) -> List[BaseProvider]:
        """应用路由规则过滤供应商 (集成 RuleEngine 功能)"""
        # 排除上次失败的供应商
        if context.previous_provider:
            providers = [p for p in providers if p.provider_type != context.previous_provider]
        
        # 根据智能体类型过滤
        if context.agent_type and context.agent_type in self.agent_optimizations:
            agent_config = self.agent_optimizations[context.agent_type]
            preferred_capabilities = agent_config.get("preferred_capabilities", [])
            
            # 优先选择具有所需能力的供应商
            preferred_providers = []
            other_providers = []
            
            for provider in providers:
                if any(cap in provider.capabilities for cap in preferred_capabilities):
                    preferred_providers.append(provider)
                else:
                    other_providers.append(provider)
            
            # 如果有优选供应商，优先使用；否则使用其他供应商
            providers = preferred_providers if preferred_providers else other_providers
        
        return providers
    
    def _score_providers(
        self,
        providers: List[BaseProvider],
        request: LLMRequest,
        context: RoutingContext,
        strategy: RoutingStrategy
    ) -> List[ProviderScore]:
        """对供应商进行评分 (集成 ScoringEngine 功能)"""
        scores = []
        
        for provider in providers:
            # 基础评分计算
            performance_score = self._calculate_performance_score(provider, context)
            cost_score = self._calculate_cost_score(provider, context, strategy)
            capability_score = self._calculate_capability_score(provider, context)
            health_score = self._calculate_health_score(provider)
            load_score = self._calculate_load_score(provider)
            
            # 根据策略计算总分
            total_score = self._calculate_total_score(
                performance_score, cost_score, capability_score, 
                health_score, load_score, strategy, context
            )
            
            score = ProviderScore(
                provider=provider,
                total_score=total_score,
                performance_score=performance_score,
                cost_score=cost_score,
                capability_score=capability_score,
                health_score=health_score,
                load_score=load_score,
                details={
                    "strategy": strategy.value,
                    "agent_type": context.agent_type,
                    "language": context.content_language
                }
            )
            scores.append(score)
        
        return sorted(scores, key=lambda x: x.total_score, reverse=True)
    
    def _select_provider(self, scores: List[ProviderScore], context: RoutingContext) -> BaseProvider:
        """选择最佳供应商 (集成 SelectionEngine 功能)"""
        if not scores:
            raise ProviderError("没有可评分的供应商")
        
        # 简单选择策略：选择评分最高的供应商
        # 加入少量随机性避免单一供应商过载
        if len(scores) > 1 and random.random() < 0.1:  # 10%概率选择次优
            return scores[1].provider
        
        return scores[0].provider
    
    def _record_routing_decision(
        self,
        request: LLMRequest,
        context: RoutingContext,
        selected_provider: BaseProvider,
        scores: List[ProviderScore],
        routing_time: float
    ):
        """记录路由决策 (集成 LearningEngine 功能)"""
        decision = {
            "timestamp": datetime.now(),
            "request_id": request.request_id,
            "agent_type": context.agent_type,
            "tenant_id": context.tenant_id,
            "selected_provider": selected_provider.provider_type.value,
            "routing_time": routing_time,
            "scores": [
                {
                    "provider": score.provider.provider_type.value,
                    "total_score": score.total_score
                }
                for score in scores[:3]  # 只记录前3名
            ]
        }
        
        self.routing_history.append(decision)
        
        # 限制历史记录大小
        if len(self.routing_history) > self.max_routing_history:
            self.routing_history = self.routing_history[-self.max_routing_history//2:]
    
    def _update_performance_metrics(
        self,
        request_id: str,
        provider_type: ProviderType,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None
    ):
        """更新性能指标 (集成 LearningEngine 功能)"""
        provider_key = provider_type.value
        
        if provider_key not in self.provider_performance:
            self.provider_performance[provider_key] = {
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "total_requests": 0,
                "successful_requests": 0
            }
        
        metrics = self.provider_performance[provider_key]
        metrics["total_requests"] += 1
        
        if success:
            metrics["successful_requests"] += 1
            # 更新平均响应时间
            old_avg = metrics["avg_response_time"]
            new_count = metrics["successful_requests"]
            metrics["avg_response_time"] = (old_avg * (new_count - 1) + response_time) / new_count
        
        # 更新成功率
        metrics["success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
    
    def _get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息 (集成 LearningEngine 功能)"""
        return {
            "total_routing_decisions": len(self.routing_history),
            "provider_performance": self.provider_performance,
            "recent_decisions": self.routing_history[-10:] if self.routing_history else []
        }
    
    # 评分计算辅助方法
    def _calculate_performance_score(self, provider: BaseProvider, context: RoutingContext) -> float:
        """计算性能评分"""
        provider_key = provider.provider_type.value
        if provider_key in self.provider_performance:
            metrics = self.provider_performance[provider_key]
            success_rate = metrics.get("success_rate", 0.5)
            avg_time = metrics.get("avg_response_time", 2.0)
            # 成功率占60%，响应时间占40%（时间越短分数越高）
            return success_rate * 0.6 + (1.0 / max(avg_time, 0.1)) * 0.4
        return 0.5  # 默认评分
    
    def _calculate_cost_score(self, provider: BaseProvider, context: RoutingContext, strategy: RoutingStrategy) -> float:
        """计算成本评分"""
        # 简化成本评分逻辑
        cost_mapping = {
            ProviderType.DEEPSEEK: 1.0,    # 最便宜
            ProviderType.GEMINI: 0.8,
            ProviderType.OPENAI: 0.6,
            ProviderType.ANTHROPIC: 0.4    # 最贵
        }
        return cost_mapping.get(provider.provider_type, 0.5)
    
    def _calculate_capability_score(self, provider: BaseProvider, context: RoutingContext) -> float:
        """计算能力评分"""
        score = 0.5  # 基础分
        
        # 中文优化
        if context.content_language == "zh" and ModelCapability.CHINESE_OPTIMIZATION in provider.capabilities:
            score += 0.3
        
        # 多模态支持
        if context.has_multimodal and ModelCapability.MULTIMODAL in provider.capabilities:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_health_score(self, provider: BaseProvider) -> float:
        """计算健康评分"""
        # 简化健康评分，实际应该检查供应商健康状态
        return 0.9  # 假设都是健康的
    
    def _calculate_load_score(self, provider: BaseProvider) -> float:
        """计算负载评分"""
        # 简化负载评分
        return 0.8  # 假设负载适中
    
    def _calculate_total_score(
        self,
        performance: float,
        cost: float,
        capability: float,
        health: float,
        load: float,
        strategy: RoutingStrategy,
        context: RoutingContext
    ) -> float:
        """计算总评分"""
        # 根据策略调整权重
        if strategy == RoutingStrategy.PERFORMANCE_FIRST:
            weights = {"performance": 0.4, "cost": 0.1, "capability": 0.3, "health": 0.1, "load": 0.1}
        elif strategy == RoutingStrategy.COST_FIRST:
            weights = {"performance": 0.2, "cost": 0.4, "capability": 0.2, "health": 0.1, "load": 0.1}
        elif strategy == RoutingStrategy.CHINESE_OPTIMIZED:
            weights = {"performance": 0.3, "cost": 0.2, "capability": 0.4, "health": 0.05, "load": 0.05}
        else:  # BALANCED or others
            weights = {"performance": 0.3, "cost": 0.25, "capability": 0.25, "health": 0.1, "load": 0.1}
        
        # 智能体特定调整
        if context.agent_type in self.agent_optimizations:
            agent_config = self.agent_optimizations[context.agent_type]
            cost_sensitivity = agent_config.get("cost_sensitivity", 0.5)
            # 调整成本权重
            weights["cost"] *= cost_sensitivity
            weights["performance"] += (1 - cost_sensitivity) * 0.1
        
        total = (
            performance * weights["performance"] +
            cost * weights["cost"] +
            capability * weights["capability"] +
            health * weights["health"] +
            load * weights["load"]
        )
        
        return min(total, 1.0)
    
