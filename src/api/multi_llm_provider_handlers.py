"""
多LLM供应商管理处理器

专门处理供应商管理和成本追踪的API逻辑。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from src.utils import get_component_logger


class ProviderManagementHandler:
    """供应商管理API处理器"""
    
    def __init__(self, multi_llm_handler):
        self.multi_llm_handler = multi_llm_handler
        self.logger = get_component_logger(__name__, "ProviderManagementHandler")
    
    async def get_provider_status_all(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取所有供应商状态"""
        try:
            client = await self.multi_llm_handler.get_client()
            provider_status = await client.get_provider_status(tenant_id)
            
            return {
                "tenant_id": tenant_id,
                "providers": provider_status,
                "healthy_providers": [
                    provider for provider, status in provider_status.items()
                    if status.get("is_healthy", False)
                ],
                "total_providers": len(provider_status),
                "overall_health": self.multi_llm_handler._get_provider_health_summary(provider_status)
            }
            
        except Exception as e:
            self.logger.error(f"获取供应商状态失败: {e}")
            raise
    
    async def get_cost_analysis_detailed(
        self,
        tenant_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取详细成本分析"""
        try:
            client = await self.multi_llm_handler.get_client()
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            cost_analysis = await client.get_cost_analysis(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time
            )
            
            # 添加额外的分析数据
            return {
                **cost_analysis,
                "analysis_period_hours": hours,
                "cost_trend": "stable",  # 这里可以添加趋势分析
                "efficiency_score": self._calculate_efficiency_score(cost_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"获取成本分析失败: {e}")
            raise
    
    def _calculate_efficiency_score(self, cost_analysis: Dict[str, Any]) -> float:
        """计算效率分数"""
        # 基于成本和请求数量计算效率分数
        avg_cost = cost_analysis.get("avg_cost_per_request", 0)
        
        if avg_cost == 0:
            return 1.0
        elif avg_cost < 0.01:
            return 0.9
        elif avg_cost < 0.05:
            return 0.8
        elif avg_cost < 0.1:
            return 0.7
        else:
            return 0.6


class OptimizationHandler:
    """优化建议API处理器"""
    
    def __init__(self, multi_llm_handler):
        self.multi_llm_handler = multi_llm_handler
        self.logger = get_component_logger(__name__, "OptimizationHandler")
    
    async def get_optimization_recommendations(
        self,
        tenant_id: Optional[str] = None,
        min_savings: float = 0.1
    ) -> Dict[str, Any]:
        """获取优化建议"""
        try:
            client = await self.multi_llm_handler.get_client()
            
            suggestions = await client.get_optimization_suggestions(
                tenant_id=tenant_id,
                min_savings=min_savings
            )
            
            return {
                "tenant_id": tenant_id,
                "total_suggestions": len(suggestions),
                "potential_total_savings": sum(s.get("potential_savings", 0) for s in suggestions),
                "suggestions": suggestions,
                "priority_suggestions": [
                    s for s in suggestions
                    if s.get("confidence", 0) > 0.8
                ]
            }
            
        except Exception as e:
            self.logger.error(f"获取优化建议失败: {e}")
            raise
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            client = await self.multi_llm_handler.get_client()
            stats = await client.get_global_stats()
            
            return {
                "global_stats": stats,
                "performance_summary": self._build_performance_summary(stats),
                "recommendations": await self._generate_performance_recommendations(stats)
            }
            
        except Exception as e:
            self.logger.error(f"获取性能指标失败: {e}")
            raise
    
    def _build_performance_summary(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """构建性能摘要"""
        client_stats = stats.get("client_stats", {})
        
        return {
            "total_requests": client_stats.get("total_requests", 0),
            "success_rate": client_stats.get("success_rate", 0.0),
            "avg_response_time": client_stats.get("avg_response_time", 0.0),
            "error_count": client_stats.get("error_count", 0)
        }
    
    async def _generate_performance_recommendations(
        self,
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成性能建议"""
        recommendations = []
        
        client_stats = stats.get("client_stats", {})
        success_rate = client_stats.get("success_rate", 1.0)
        avg_response_time = client_stats.get("avg_response_time", 0.0)
        
        if success_rate < 0.95:
            recommendations.append({
                "type": "reliability",
                "message": "成功率偏低，建议检查供应商健康状态",
                "priority": "high"
            })
        
        if avg_response_time > 2000:  # 2秒
            recommendations.append({
                "type": "performance",
                "message": "响应时间较慢，建议优化供应商选择策略",
                "priority": "medium"
            })
        
        return recommendations