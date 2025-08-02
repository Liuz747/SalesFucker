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
from src.utils import get_component_logger, ErrorHandler


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
            
            # 应用路由规则过滤
            filtered_providers = await self._apply_routing_rules(
                available_providers, request, context
            )
            
            if not filtered_providers:
                # 如果规则过滤后没有可用供应商，回退到所有可用供应商
                filtered_providers = available_providers
                self.logger.warning("路由规则过滤后无可用供应商，回退到全部供应商")
            
            # 计算供应商评分
            provider_scores = await self._score_providers(
                filtered_providers, request, context, strategy
            )
            
            # 选择最优供应商
            selected_provider = self._select_provider(provider_scores, context)
            
            # 记录路由决策
            routing_time = time.time() - start_time
            await self._record_routing_decision(
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
        await self.learning_engine.update_performance_metrics(
            request_id, provider_type, success, response_time, error_type
        )
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return self.learning_engine.get_routing_stats()
    
    def get_agent_optimizations(self) -> Dict[str, Any]:
        """获取智能体优化配置"""
        return self.scoring_engine.get_agent_optimizations()
    
