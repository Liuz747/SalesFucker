"""
优化建议引擎模块

负责生成智能的成本优化建议。
"""

from typing import List, Dict, Any
from collections import defaultdict

from .models import CostAnalysis, OptimizationSuggestion, OptimizationType
from .benchmark_data import BenchmarkData
from ..provider_config import ProviderType


class SuggestionEngine:
    """优化建议引擎类"""
    
    def __init__(self):
        """初始化建议引擎"""
        self.optimization_strategies = {
            OptimizationType.PROVIDER_SWITCH: {
                "min_savings_threshold": 0.2,
                "confidence_threshold": 0.8
            },
            OptimizationType.MODEL_DOWNGRADE: {
                "min_savings_threshold": 0.15,
                "confidence_threshold": 0.7,
                "quality_impact_threshold": 0.1
            },
            OptimizationType.CACHE_STRATEGY: {
                "min_cache_hit_rate": 0.3,
                "cache_cost_reduction": 0.9
            }
        }
    
    async def generate_suggestions(
        self,
        analysis: CostAnalysis,
        benchmark_data: BenchmarkData,
        min_savings: float
    ) -> List[OptimizationSuggestion]:
        """
        生成优化建议
        
        参数:
            analysis: 成本分析结果
            benchmark_data: 基准数据
            min_savings: 最小节省比例
            
        返回:
            List[OptimizationSuggestion]: 优化建议列表
        """
        suggestions = []
        
        # 供应商切换建议
        provider_suggestions = await self._analyze_provider_switching(
            analysis, benchmark_data, min_savings
        )
        suggestions.extend(provider_suggestions)
        
        # 模型降级建议
        model_suggestions = await self._analyze_model_downgrading(
            analysis, min_savings
        )
        suggestions.extend(model_suggestions)
        
        # 缓存策略建议
        cache_suggestions = await self._analyze_cache_opportunities(
            analysis, min_savings
        )
        suggestions.extend(cache_suggestions)
        
        # 按节省潜力排序
        suggestions.sort(key=lambda x: x.potential_savings, reverse=True)
        
        return suggestions
    
    async def _analyze_provider_switching(
        self,
        analysis: CostAnalysis,
        benchmark_data: BenchmarkData,
        min_savings: float
    ) -> List[OptimizationSuggestion]:
        """分析供应商切换机会"""
        suggestions = []
        
        for provider, cost in analysis.provider_breakdown.items():
            if cost / analysis.total_cost > 0.3:  # 占总成本30%以上
                cheaper_alternatives = benchmark_data.find_cheaper_alternatives(provider)
                
                for alternative in cheaper_alternatives:
                    potential_savings = cost * alternative["savings_rate"]
                    if potential_savings / analysis.total_cost >= min_savings:
                        suggestions.append(OptimizationSuggestion(
                            optimization_type=OptimizationType.PROVIDER_SWITCH,
                            current_cost=cost,
                            potential_savings=potential_savings,
                            savings_percentage=alternative["savings_rate"],
                            confidence=alternative["confidence"],
                            description=f"将 {provider} 切换到 {alternative['provider']} 可节省成本",
                            implementation_details={
                                "from_provider": provider,
                                "to_provider": alternative["provider"],
                                "affected_requests": alternative.get("affected_requests", 0)
                            },
                            estimated_impact={
                                "quality_impact": alternative.get("quality_impact", 0.0),
                                "response_time_impact": alternative.get("response_time_impact", 0.0)
                            }
                        ))
        
        return suggestions
    
    async def _analyze_model_downgrading(
        self,
        analysis: CostAnalysis,
        min_savings: float
    ) -> List[OptimizationSuggestion]:
        """分析模型降级机会"""
        suggestions = []
        
        # 这里需要从外部获取记录数据来分析模型使用情况
        # 为简化示例，使用placeholder逻辑
        expensive_model_patterns = ["gpt-4", "claude-3-opus"]
        
        for pattern in expensive_model_patterns:
            # 估算高成本模型的使用
            estimated_cost = analysis.total_cost * 0.3  # 假设占30%
            if estimated_cost / analysis.total_cost > 0.2:
                potential_savings = estimated_cost * 0.7
                
                if potential_savings / analysis.total_cost >= min_savings:
                    suggestions.append(OptimizationSuggestion(
                        optimization_type=OptimizationType.MODEL_DOWNGRADE,
                        current_cost=estimated_cost,
                        potential_savings=potential_savings,
                        savings_percentage=0.7,
                        confidence=0.6,
                        description=f"将高端模型降级到更经济的替代品",
                        implementation_details={
                            "current_model_pattern": pattern,
                            "suggested_alternatives": ["gpt-3.5-turbo", "claude-3-haiku"],
                            "estimated_requests": int(analysis.total_requests * 0.3)
                        },
                        estimated_impact={
                            "quality_impact": 0.15,
                            "response_time_impact": -0.1
                        }
                    ))
        
        return suggestions
    
    async def _analyze_cache_opportunities(
        self,
        analysis: CostAnalysis,
        min_savings: float
    ) -> List[OptimizationSuggestion]:
        """分析缓存策略机会"""
        suggestions = []
        
        # 估算可缓存的请求成本
        cacheable_cost = analysis.total_cost * 0.4  # 假设40%的请求可以被缓存
        
        if cacheable_cost > 0:
            potential_savings = cacheable_cost * 0.9  # 缓存可节省90%成本
            
            if potential_savings / analysis.total_cost >= min_savings:
                suggestions.append(OptimizationSuggestion(
                    optimization_type=OptimizationType.CACHE_STRATEGY,
                    current_cost=cacheable_cost,
                    potential_savings=potential_savings,
                    savings_percentage=0.9,
                    confidence=0.7,
                    description="实施智能缓存策略可节省重复请求成本",
                    implementation_details={
                        "cacheable_requests": int(analysis.total_requests * 0.4),
                        "cache_hit_rate_estimate": 0.8,
                        "cache_duration": "1小时"
                    },
                    estimated_impact={
                        "quality_impact": 0.0,
                        "response_time_impact": -0.8
                    }
                ))
        
        return suggestions