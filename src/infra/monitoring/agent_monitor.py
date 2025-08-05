"""
智能体监控模块

该模块提供智能体的统计信息收集、健康状态监控和性能追踪功能。
专为开发团队仪表板提供数据支持。

核心功能:
- 处理统计信息管理
- 健康状态评估
- 性能指标追踪
- LLM调用监控
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from src.utils import get_current_datetime, get_processing_time_ms


@dataclass
class ProcessingStats:
    """处理统计信息"""
    messages_processed: int = 0
    errors: int = 0
    last_activity: Optional[str] = None
    average_response_time: float = 0.0
    total_processing_time: float = 0.0


@dataclass
class LLMStats:
    """LLM统计信息"""
    total_llm_requests: int = 0
    successful_llm_requests: int = 0
    failed_llm_requests: int = 0
    total_llm_cost: float = 0.0
    avg_llm_response_time: float = 0.0
    provider_usage: Dict[str, int] = field(default_factory=dict)


class AgentMonitor:
    """
    智能体监控器
    
    负责收集和管理智能体的统计信息、健康状态和性能指标。
    为开发团队仪表板提供数据支持。
    """
    
    def __init__(self, agent_id: str, agent_type: str, tenant_id: Optional[str] = None):
        """
        初始化监控器
        
        参数:
            agent_id: 智能体唯一标识符
            agent_type: 智能体类型
            tenant_id: 租户标识符
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.tenant_id = tenant_id
        
        # 统计信息
        self.processing_stats = ProcessingStats()
        self.llm_stats = LLMStats()
        
        # 启动时间
        self.start_time = get_current_datetime()
        
    def update_processing_stats(self, processing_time: float = 0.0):
        """
        更新处理统计信息
        
        参数:
            processing_time: 处理耗时(秒)
        """
        self.processing_stats.messages_processed += 1
        self.processing_stats.last_activity = get_current_datetime()
        
        if processing_time > 0:
            total_time = self.processing_stats.total_processing_time + processing_time
            self.processing_stats.total_processing_time = total_time
            
            # 计算平均响应时间
            self.processing_stats.average_response_time = (
                total_time / self.processing_stats.messages_processed
            )
    
    def record_error(self):
        """记录错误"""
        self.processing_stats.errors += 1
    
    def update_llm_stats(self, processing_time: float, success: bool, cost: float = 0.0, provider: str = ""):
        """
        更新LLM统计信息
        
        参数:
            processing_time: 处理耗时(秒)
            success: 是否成功
            cost: 调用费用
            provider: 提供商名称
        """
        self.llm_stats.total_llm_requests += 1
        self.llm_stats.total_llm_cost += cost
        
        if provider:
            self.llm_stats.provider_usage[provider] = self.llm_stats.provider_usage.get(provider, 0) + 1
        
        if success:
            self.llm_stats.successful_llm_requests += 1
            
            # 更新平均响应时间
            total_successful = self.llm_stats.successful_llm_requests
            current_avg = self.llm_stats.avg_llm_response_time
            self.llm_stats.avg_llm_response_time = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
        else:
            self.llm_stats.failed_llm_requests += 1
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """获取处理指标"""
        return {
            "messages_processed": self.processing_stats.messages_processed,
            "errors": self.processing_stats.errors,
            "last_activity": self.processing_stats.last_activity,
            "average_response_time": self.processing_stats.average_response_time,
            "total_processing_time": self.processing_stats.total_processing_time,
            "uptime_seconds": get_processing_time_ms(self.start_time)
        }
    
    def get_llm_metrics(self) -> Dict[str, Any]:
        """获取LLM指标"""
        return {
            "total_llm_requests": self.llm_stats.total_llm_requests,
            "successful_llm_requests": self.llm_stats.successful_llm_requests,
            "failed_llm_requests": self.llm_stats.failed_llm_requests,
            "total_llm_cost": self.llm_stats.total_llm_cost,
            "avg_llm_response_time": self.llm_stats.avg_llm_response_time,
            "provider_usage": self.llm_stats.provider_usage.copy()
        }
    
    def calculate_error_rate(self) -> float:
        """计算错误率"""
        total_processed = self.processing_stats.messages_processed
        if total_processed == 0:
            return 0.0
        return (self.processing_stats.errors / total_processed)
    
    def calculate_llm_error_rate(self) -> float:
        """计算LLM错误率"""
        total_requests = self.llm_stats.total_llm_requests
        if total_requests == 0:
            return 0.0
        return (self.llm_stats.failed_llm_requests / total_requests)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态信息"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tenant_id": self.tenant_id,
            "processing_metrics": self.get_processing_metrics(),
            "llm_metrics": self.get_llm_metrics(),
            "error_rates": {
                "processing_error_rate": self.calculate_error_rate(),
                "llm_error_rate": self.calculate_llm_error_rate()
            },
            "error_counts": {
                "processing_errors": self.processing_stats.errors,
                "failed_llm_requests": self.llm_stats.failed_llm_requests
            }
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.processing_stats = ProcessingStats()
        self.llm_stats = LLMStats()
        self.start_time = get_current_datetime()