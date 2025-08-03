"""
统计收集器模块

该模块负责收集和管理多LLM客户端的性能统计数据。
提供详细的性能指标跟踪和分析功能。

核心功能:
- 请求统计收集
- 性能指标计算
- 成本追踪
- 供应商使用统计
"""

import time
from typing import Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime
from collections import defaultdict

from ..base_provider import LLMRequest, LLMResponse
from src.utils import get_component_logger


class StatsCollector:
    """
    统计收集器
    
    负责收集和维护多LLM客户端的各种统计信息。
    """
    
    def __init__(self):
        """初始化统计收集器"""
        self.logger = get_component_logger(__name__, "StatsCollector")
        
        # 基础统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "provider_usage": defaultdict(int),
            "cost_metrics": defaultdict(float)
        }
        
        # 详细统计
        self.detailed_stats = {
            "agent_type_usage": defaultdict(int),
            "tenant_usage": defaultdict(int),
            "model_usage": defaultdict(int),
            "error_types": defaultdict(int),
            "avg_response_times": defaultdict(list),
            "hourly_usage": defaultdict(int)
        }
    
    def record_request_start(self, request: LLMRequest) -> str:
        """
        记录请求开始
        
        参数:
            request: LLM请求对象
            
        返回:
            str: 统计会话ID
        """
        session_id = f"{request.request_id}_{int(time.time())}"
        
        # 更新基础统计
        self.stats["total_requests"] += 1
        
        # 更新详细统计
        if request.agent_type:
            self.detailed_stats["agent_type_usage"][request.agent_type] += 1
        
        if request.tenant_id:
            self.detailed_stats["tenant_usage"][request.tenant_id] += 1
        
        # 小时级使用统计
        hour_key = datetime.now().strftime("%Y-%m-%d_%H")
        self.detailed_stats["hourly_usage"][hour_key] += 1
        
        self.logger.debug(f"记录请求开始: {request.request_id}")
        return session_id
    
    def record_request_success(
        self,
        request: LLMRequest,
        response: Union[LLMResponse, AsyncGenerator],
        processing_time: float
    ):
        """
        记录成功请求
        
        参数:
            request: LLM请求对象
            response: LLM响应对象
            processing_time: 处理时间
        """
        # 更新成功统计
        self.stats["successful_requests"] += 1
        self.stats["total_response_time"] += processing_time
        
        # 记录供应商使用
        if isinstance(response, LLMResponse):
            provider = response.provider_type.value
            self.stats["provider_usage"][provider] += 1
            
            # 记录模型使用
            if response.model:
                self.detailed_stats["model_usage"][response.model] += 1
            
            # 记录响应时间
            self.detailed_stats["avg_response_times"][provider].append(processing_time)
            
            # 保持响应时间列表大小
            if len(self.detailed_stats["avg_response_times"][provider]) > 1000:
                self.detailed_stats["avg_response_times"][provider] = \
                    self.detailed_stats["avg_response_times"][provider][-500:]
        
        self.logger.debug(f"记录成功请求: {request.request_id}, 耗时: {processing_time:.3f}s")
    
    def record_request_failure(
        self,
        request: LLMRequest,
        error: Exception,
        processing_time: float
    ):
        """
        记录失败请求
        
        参数:
            request: LLM请求对象
            error: 错误信息
            processing_time: 处理时间
        """
        # 更新失败统计
        self.stats["failed_requests"] += 1
        
        # 记录错误类型
        error_type = type(error).__name__
        self.detailed_stats["error_types"][error_type] += 1
        
        self.logger.debug(f"记录失败请求: {request.request_id}, 错误: {error_type}")
    
    def record_cost(
        self,
        provider_type: str,
        cost: float,
        agent_type: Optional[str] = None
    ):
        """
        记录成本
        
        参数:
            provider_type: 供应商类型
            cost: 成本
            agent_type: 智能体类型
        """
        self.stats["cost_metrics"][provider_type] += cost
        
        if agent_type:
            agent_cost_key = f"{agent_type}_{provider_type}"
            self.stats["cost_metrics"][agent_cost_key] += cost
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """获取基础统计信息"""
        stats_copy = self.stats.copy()
        
        # 计算平均响应时间
        if stats_copy["successful_requests"] > 0:
            stats_copy["avg_response_time"] = (
                stats_copy["total_response_time"] / stats_copy["successful_requests"]
            )
        else:
            stats_copy["avg_response_time"] = 0.0
        
        # 计算成功率
        if stats_copy["total_requests"] > 0:
            stats_copy["success_rate"] = (
                stats_copy["successful_requests"] / stats_copy["total_requests"]
            )
        else:
            stats_copy["success_rate"] = 0.0
        
        return stats_copy
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        detailed_copy = {}
        
        # 复制基础数据
        for key, value in self.detailed_stats.items():
            if isinstance(value, defaultdict):
                detailed_copy[key] = dict(value)
            else:
                detailed_copy[key] = value
        
        # 计算平均响应时间
        provider_avg_times = {}
        for provider, times in self.detailed_stats["avg_response_times"].items():
            if times:
                provider_avg_times[provider] = sum(times) / len(times)
            else:
                provider_avg_times[provider] = 0.0
        
        detailed_copy["provider_avg_response_times"] = provider_avg_times
        
        return detailed_copy
    
    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计信息"""
        return {
            "basic_stats": self.get_basic_stats(),
            "detailed_stats": self.get_detailed_stats(),
            "collection_time": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "provider_usage": defaultdict(int),
            "cost_metrics": defaultdict(float)
        }
        
        self.detailed_stats = {
            "agent_type_usage": defaultdict(int),
            "tenant_usage": defaultdict(int),
            "model_usage": defaultdict(int),
            "error_types": defaultdict(int),
            "avg_response_times": defaultdict(list),
            "hourly_usage": defaultdict(int)
        }
        
        self.logger.info("统计信息已重置")
    
    def get_usage_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        获取使用摘要
        
        参数:
            time_window_hours: 时间窗口（小时）
            
        返回:
            Dict[str, Any]: 使用摘要
        """
        current_time = datetime.now()
        summary = {
            "time_window_hours": time_window_hours,
            "total_requests_in_window": 0,
            "top_agents": {},
            "top_tenants": {},
            "top_providers": {},
            "error_summary": {}
        }
        
        # 计算时间窗口内的请求数
        for i in range(time_window_hours):
            hour_time = current_time.replace(minute=0, second=0, microsecond=0)
            hour_time = hour_time.replace(hour=hour_time.hour - i)
            hour_key = hour_time.strftime("%Y-%m-%d_%H")
            
            summary["total_requests_in_window"] += self.detailed_stats["hourly_usage"].get(hour_key, 0)
        
        # 获取前5名
        summary["top_agents"] = dict(
            sorted(self.detailed_stats["agent_type_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["top_tenants"] = dict(
            sorted(self.detailed_stats["tenant_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["top_providers"] = dict(
            sorted(self.stats["provider_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["error_summary"] = dict(self.detailed_stats["error_types"])
        
        return summary