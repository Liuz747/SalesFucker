"""
统计收集器模块

负责收集和管理LLM客户端的性能统计信息。
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..base_provider import LLMResponse
from ..provider_config import ProviderType
from src.utils import get_component_logger


class RequestStats:
    """请求统计信息"""
    
    def __init__(self):
        """初始化请求统计"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        self.total_tokens = 0
        self.total_cost = 0.0
        
        # 性能指标
        self.min_response_time = float('inf')
        self.max_response_time = 0.0
        self.response_times = deque(maxlen=1000)  # 保留最近1000次请求的响应时间
    
    def add_request(
        self, 
        success: bool, 
        response_time: float, 
        tokens: int = 0, 
        cost: float = 0.0
    ):
        """添加请求统计"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_response_time += response_time
        self.total_tokens += tokens
        self.total_cost += cost
        
        # 更新性能指标
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        self.response_times.append(response_time)
    
    @property
    def average_response_time(self) -> float:
        """平均响应时间"""
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """95分位响应时间"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]


class StatsCollector:
    """统计收集器"""
    
    def __init__(self, window_size_minutes: int = 60):
        """
        初始化统计收集器
        
        参数:
            window_size_minutes: 统计窗口大小（分钟）
        """
        self.logger = get_component_logger(__name__, "StatsCollector")
        self.window_size = timedelta(minutes=window_size_minutes)
        
        # 全局统计
        self.global_stats = RequestStats()
        
        # 按供应商统计
        self.provider_stats: Dict[str, RequestStats] = defaultdict(RequestStats)
        
        # 按租户统计
        self.tenant_stats: Dict[str, RequestStats] = defaultdict(RequestStats)
        
        # 按智能体类型统计
        self.agent_stats: Dict[str, RequestStats] = defaultdict(RequestStats)
        
        # 时间窗口统计
        self.hourly_stats: List[Dict[str, Any]] = []
        
        # 成本统计
        self.cost_by_provider: Dict[str, float] = defaultdict(float)
        self.cost_by_tenant: Dict[str, float] = defaultdict(float)
        
        # 错误统计
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        self.logger.debug("统计收集器初始化完成")
    
    def record_request_start(self, request_id: str) -> float:
        """
        记录请求开始
        
        参数:
            request_id: 请求ID
            
        返回:
            float: 开始时间戳
        """
        start_time = time.time()
        self.logger.debug(f"记录请求开始: {request_id}")
        return start_time
    
    def record_request_completion(
        self,
        request_id: str,
        start_time: float,
        response: Optional[LLMResponse] = None,
        error: Optional[Exception] = None,
        tenant_id: Optional[str] = None,
        agent_type: Optional[str] = None
    ):
        """
        记录请求完成
        
        参数:
            request_id: 请求ID
            start_time: 开始时间戳
            response: 响应对象
            error: 错误对象
            tenant_id: 租户ID
            agent_type: 智能体类型
        """
        end_time = time.time()
        response_time = end_time - start_time
        success = error is None
        
        # 提取统计信息
        tokens = 0
        cost = 0.0
        provider_type = None
        
        if response:
            if response.usage:
                tokens = response.usage.total_tokens
            if response.cost:
                cost = response.cost
            provider_type = response.provider_type
        
        # 更新全局统计
        self.global_stats.add_request(success, response_time, tokens, cost)
        
        # 更新供应商统计
        if provider_type:
            provider_key = provider_type.value if isinstance(provider_type, ProviderType) else str(provider_type)
            self.provider_stats[provider_key].add_request(success, response_time, tokens, cost)
            self.cost_by_provider[provider_key] += cost
        
        # 更新租户统计
        if tenant_id:
            self.tenant_stats[tenant_id].add_request(success, response_time, tokens, cost)
            self.cost_by_tenant[tenant_id] += cost
        
        # 更新智能体统计
        if agent_type:
            self.agent_stats[agent_type].add_request(success, response_time, tokens, cost)
        
        # 记录错误
        if error:
            error_type = type(error).__name__
            self.error_counts[error_type] += 1
        
        self.logger.debug(f"记录请求完成: {request_id}, 成功: {success}, 响应时间: {response_time:.3f}s")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        返回:
            Dict[str, Any]: 全局统计信息
        """
        stats = self.global_stats
        
        return {
            "total_requests": stats.total_requests,
            "successful_requests": stats.successful_requests,
            "failed_requests": stats.failed_requests,
            "success_rate": stats.success_rate,
            "total_response_time": stats.total_response_time,
            "average_response_time": stats.average_response_time,
            "min_response_time": stats.min_response_time if stats.min_response_time != float('inf') else 0.0,
            "max_response_time": stats.max_response_time,
            "p95_response_time": stats.p95_response_time,
            "total_tokens": stats.total_tokens,
            "total_cost": stats.total_cost
        }
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取供应商统计信息
        
        返回:
            Dict[str, Dict[str, Any]]: 供应商统计信息
        """
        result = {}
        
        for provider, stats in self.provider_stats.items():
            result[provider] = {
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "success_rate": stats.success_rate,
                "average_response_time": stats.average_response_time,
                "p95_response_time": stats.p95_response_time,
                "total_tokens": stats.total_tokens,
                "total_cost": self.cost_by_provider[provider]
            }
        
        return result
    
    def get_tenant_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取租户统计信息
        
        返回:
            Dict[str, Dict[str, Any]]: 租户统计信息
        """
        result = {}
        
        for tenant_id, stats in self.tenant_stats.items():
            result[tenant_id] = {
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "success_rate": stats.success_rate,
                "average_response_time": stats.average_response_time,
                "total_tokens": stats.total_tokens,
                "total_cost": self.cost_by_tenant[tenant_id]
            }
        
        return result
    
    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取智能体统计信息
        
        返回:
            Dict[str, Dict[str, Any]]: 智能体统计信息
        """
        result = {}
        
        for agent_type, stats in self.agent_stats.items():
            result[agent_type] = {
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "success_rate": stats.success_rate,
                "average_response_time": stats.average_response_time,
                "total_tokens": stats.total_tokens
            }
        
        return result
    
    def get_error_stats(self) -> Dict[str, int]:
        """
        获取错误统计信息
        
        返回:
            Dict[str, int]: 错误统计信息
        """
        return dict(self.error_counts)
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """
        获取成本分解信息
        
        返回:
            Dict[str, Any]: 成本分解信息
        """
        return {
            "total_cost": self.global_stats.total_cost,
            "by_provider": dict(self.cost_by_provider),
            "by_tenant": dict(self.cost_by_tenant)
        }
    
    def reset_stats(self):
        """重置所有统计信息"""
        self.global_stats = RequestStats()
        self.provider_stats.clear()
        self.tenant_stats.clear()
        self.agent_stats.clear()
        self.cost_by_provider.clear()
        self.cost_by_tenant.clear()
        self.error_counts.clear()
        self.hourly_stats.clear()
        
        self.logger.info("统计信息已重置")
    
    def export_stats(self) -> Dict[str, Any]:
        """
        导出所有统计信息
        
        返回:
            Dict[str, Any]: 完整的统计信息
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "global": self.get_global_stats(),
            "providers": self.get_provider_stats(),
            "tenants": self.get_tenant_stats(),
            "agents": self.get_agent_stats(),
            "errors": self.get_error_stats(),
            "costs": self.get_cost_breakdown()
        }