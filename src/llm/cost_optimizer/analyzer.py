"""
成本分析器模块

负责成本数据的分析和趋势计算。
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from .models import CostRecord, CostAnalysis


class CostAnalyzer:
    """成本分析器类"""
    
    def __init__(self):
        """初始化成本分析器"""
        pass
    
    async def analyze_records(
        self,
        records: List[CostRecord],
        start_time: datetime,
        end_time: datetime
    ) -> CostAnalysis:
        """
        分析成本记录
        
        参数:
            records: 成本记录列表
            start_time: 开始时间
            end_time: 结束时间
            
        返回:
            CostAnalysis: 分析结果
        """
        if not records:
            return self._create_empty_analysis(start_time, end_time)
        
        # 计算基础统计
        total_cost = sum(record.cost for record in records)
        total_requests = len(records)
        total_tokens = sum(record.total_tokens for record in records)
        
        avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        avg_cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0
        
        # 生成各种分解统计
        provider_breakdown = self._calculate_provider_breakdown(records)
        agent_breakdown = self._calculate_agent_breakdown(records)
        tenant_breakdown = self._calculate_tenant_breakdown(records)
        
        # 计算成本趋势
        cost_trends = self._calculate_cost_trends(records, start_time, end_time)
        
        # 识别优化机会
        optimization_opportunities = await self._identify_optimization_opportunities(records)
        
        return CostAnalysis(
            period_start=start_time,
            period_end=end_time,
            total_cost=total_cost,
            total_requests=total_requests,
            total_tokens=total_tokens,
            avg_cost_per_request=avg_cost_per_request,
            avg_cost_per_token=avg_cost_per_token,
            provider_breakdown=provider_breakdown,
            agent_breakdown=agent_breakdown,
            tenant_breakdown=tenant_breakdown,
            cost_trends=cost_trends,
            optimization_opportunities=optimization_opportunities
        )
    
    def _create_empty_analysis(self, start_time: datetime, end_time: datetime) -> CostAnalysis:
        """创建空的分析结果"""
        return CostAnalysis(
            period_start=start_time,
            period_end=end_time,
            total_cost=0.0,
            total_requests=0,
            total_tokens=0,
            avg_cost_per_request=0.0,
            avg_cost_per_token=0.0,
            provider_breakdown={},
            agent_breakdown={},
            tenant_breakdown={},
            cost_trends={},
            optimization_opportunities=[]
        )
    
    def _calculate_provider_breakdown(self, records: List[CostRecord]) -> Dict[str, float]:
        """计算供应商成本分解"""
        breakdown = defaultdict(float)
        for record in records:
            breakdown[record.provider_type.value] += record.cost
        return dict(breakdown)
    
    def _calculate_agent_breakdown(self, records: List[CostRecord]) -> Dict[str, float]:
        """计算智能体成本分解"""
        breakdown = defaultdict(float)
        for record in records:
            if record.agent_type:
                breakdown[record.agent_type] += record.cost
        return dict(breakdown)
    
    def _calculate_tenant_breakdown(self, records: List[CostRecord]) -> Dict[str, float]:
        """计算租户成本分解"""
        breakdown = defaultdict(float)
        for record in records:
            tenant_key = record.tenant_id or "default"
            breakdown[tenant_key] += record.cost
        return dict(breakdown)
    
    def _calculate_cost_trends(
        self,
        records: List[CostRecord],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[float]]:
        """计算成本趋势"""
        trends = {
            "daily_costs": [],
            "hourly_costs": [],
            "provider_trends": defaultdict(list)
        }
        
        # 按天分组计算日成本
        time_delta = end_time - start_time
        days = max(1, time_delta.days)
        
        for day in range(days):
            day_start = start_time + timedelta(days=day)
            day_end = day_start + timedelta(days=1)
            
            day_records = [
                r for r in records 
                if day_start <= r.timestamp < day_end
            ]
            
            day_cost = sum(r.cost for r in day_records)
            trends["daily_costs"].append(day_cost)
        
        # 按小时分组计算最近24小时的成本
        last_24h_start = end_time - timedelta(hours=24)
        last_24h_records = [
            r for r in records 
            if r.timestamp >= last_24h_start
        ]
        
        for hour in range(24):
            hour_start = last_24h_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_records = [
                r for r in last_24h_records 
                if hour_start <= r.timestamp < hour_end
            ]
            
            hour_cost = sum(r.cost for r in hour_records)
            trends["hourly_costs"].append(hour_cost)
        
        return dict(trends)
    
    async def _identify_optimization_opportunities(
        self,
        records: List[CostRecord]
    ) -> List[Dict[str, Any]]:
        """识别优化机会"""
        opportunities = []
        
        # 高成本供应商识别
        provider_costs = defaultdict(float)
        for record in records:
            provider_costs[record.provider_type.value] += record.cost
        
        if provider_costs:
            most_expensive_provider = max(provider_costs.items(), key=lambda x: x[1])
            total_cost = sum(provider_costs.values())
            
            if most_expensive_provider[1] / total_cost > 0.6:  # 超过60%成本
                opportunities.append({
                    "type": "high_cost_provider",
                    "description": f"供应商 {most_expensive_provider[0]} 占总成本的 {most_expensive_provider[1]/total_cost*100:.1f}%",
                    "cost_impact": most_expensive_provider[1],
                    "suggestion": "考虑使用更经济的替代供应商"
                })
        
        # 低效模型识别
        model_efficiency = defaultdict(lambda: {"cost": 0.0, "tokens": 0})
        for record in records:
            key = f"{record.provider_type.value}_{record.model_name}"
            model_efficiency[key]["cost"] += record.cost
            model_efficiency[key]["tokens"] += record.total_tokens
        
        for model_key, data in model_efficiency.items():
            if data["tokens"] > 0:
                cost_per_token = data["cost"] / data["tokens"]
                if cost_per_token > 0.00005:  # 高于平均成本
                    opportunities.append({
                        "type": "expensive_model",
                        "description": f"模型 {model_key} 每token成本较高: ${cost_per_token:.6f}",
                        "cost_impact": data["cost"],
                        "suggestion": "考虑使用更经济的模型"
                    })
        
        return opportunities