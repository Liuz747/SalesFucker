"""
学习引擎模块

负责记录和学习路由决策，提供性能指标。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..base_provider import BaseProvider, LLMRequest
from ..provider_config import ProviderType
from .models import RoutingContext, ProviderScore


class LearningEngine:
    """学习引擎类"""
    
    def __init__(self):
        """初始化学习引擎"""
        self.routing_history: List[Dict[str, Any]] = []
        self.provider_performance: Dict[str, Dict[str, float]] = {}
        self.agent_preferences: Dict[str, Dict[str, float]] = {}
        self.max_routing_history = 10000
        self.learning_window = timedelta(hours=24)
    
    async def record_routing_decision(
        self,
        request: LLMRequest,
        context: RoutingContext,
        selected_provider: BaseProvider,
        all_scores: List[ProviderScore],
        routing_time: float
    ):
        """记录路由决策用于学习"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "agent_type": context.agent_type,
            "tenant_id": context.tenant_id,
            "selected_provider": selected_provider.provider_type.value,
            "routing_time": routing_time,
            "scores": {
                score.provider.provider_type.value: {
                    "total_score": score.total_score,
                    "performance": score.performance_score,
                    "cost": score.cost_score,
                    "capability": score.capability_score,
                    "health": score.health_score,
                    "load": score.load_score
                }
                for score in all_scores
            },
            "context": {
                "content_language": context.content_language,
                "has_multimodal": context.has_multimodal,
                "urgency_level": context.urgency_level,
                "retry_count": context.retry_count
            }
        }
        
        self.routing_history.append(record)
        
        # 清理旧记录
        if len(self.routing_history) > self.max_routing_history:
            self.routing_history = self.routing_history[-self.max_routing_history:]
    
    async def update_performance_metrics(
        self,
        request_id: str,
        provider_type: ProviderType,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None
    ):
        """更新供应商性能指标"""
        # 找到对应的路由记录
        routing_record = None
        for record in reversed(self.routing_history):
            if record["request_id"] == request_id:
                routing_record = record
                break
        
        if not routing_record:
            return
        
        # 更新供应商性能数据
        provider_key = f"{provider_type}_{routing_record.get('tenant_id', 'default')}"
        
        if provider_key not in self.provider_performance:
            self.provider_performance[provider_key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_response_time": 0.0,
                "error_types": {}
            }
        
        perf_data = self.provider_performance[provider_key]
        perf_data["total_requests"] += 1
        perf_data["total_response_time"] += response_time
        
        if success:
            perf_data["successful_requests"] += 1
        else:
            if error_type:
                perf_data["error_types"][error_type] = perf_data["error_types"].get(error_type, 0) + 1
        
        # 计算衍生指标
        perf_data["success_rate"] = perf_data["successful_requests"] / perf_data["total_requests"]
        perf_data["avg_response_time"] = perf_data["total_response_time"] / perf_data["total_requests"]
        
        # 更新智能体偏好
        agent_type = routing_record.get("agent_type")
        if agent_type:
            agent_key = f"{agent_type}_{provider_type}"
            if agent_key not in self.agent_preferences:
                self.agent_preferences[agent_key] = {
                    "requests": 0,
                    "successes": 0,
                    "total_score": 1.0
                }
            
            agent_perf = self.agent_preferences[agent_key]
            agent_perf["requests"] += 1
            
            if success:
                agent_perf["successes"] += 1
                agent_perf["total_score"] = min(1.5, agent_perf["total_score"] * 1.01)
            else:
                agent_perf["total_score"] = max(0.5, agent_perf["total_score"] * 0.95)
    
    def get_provider_performance(self, provider_key: str) -> Optional[Dict[str, float]]:
        """获取供应商性能数据"""
        return self.provider_performance.get(provider_key)
    
    def get_agent_preferences(self, agent_key: str) -> Optional[Dict[str, float]]:
        """获取智能体偏好数据"""
        return self.agent_preferences.get(agent_key)
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        if not self.routing_history:
            return {"total_routes": 0}
        
        recent_routes = [
            r for r in self.routing_history 
            if datetime.fromisoformat(r["timestamp"]) > datetime.now() - timedelta(hours=24)
        ]
        
        # 供应商使用统计
        provider_usage = {}
        for record in recent_routes:
            provider = record["selected_provider"]
            provider_usage[provider] = provider_usage.get(provider, 0) + 1
        
        # 智能体类型统计
        agent_usage = {}
        for record in recent_routes:
            agent_type = record["agent_type"]
            if agent_type:
                agent_usage[agent_type] = agent_usage.get(agent_type, 0) + 1
        
        # 平均路由时间
        avg_routing_time = (
            sum(r["routing_time"] for r in recent_routes) / len(recent_routes) 
            if recent_routes else 0
        )
        
        return {
            "total_routes": len(self.routing_history),
            "recent_routes_24h": len(recent_routes),
            "avg_routing_time": avg_routing_time,
            "provider_usage": provider_usage,
            "agent_usage": agent_usage,
            "performance_data": dict(self.provider_performance),
            "agent_preferences": dict(self.agent_preferences)
        }