"""
合规性能指标模块

该模块负责合规检查的性能监控和统计分析。
从主智能体中分离出来，专注于性能指标收集和报告。

核心功能:
- 性能统计收集
- 指标分析和报告
- 性能趋势监控
- 系统健康检查
"""

from typing import Dict, Any, Optional
from datetime import datetime

from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time_ms,
    to_isoformat
)


class ComplianceMetricsManager:
    """
    合规性能指标管理器
    
    负责收集、分析和报告合规检查的性能指标，
    为系统优化和监控提供数据支持。
    
    属性:
        processing_metrics: 处理统计信息
        agent_id: 智能体标识符
        start_time: 启动时间
    """
    
    def __init__(self, agent_id: str = "compliance"):
        """
        初始化性能指标管理器

        参数:
            agent_id: 智能体标识符
        """
        self.agent_id = agent_id
        self.start_time = get_current_datetime()
        
        # 性能统计
        self.processing_metrics = {
            "total_checks": 0,
            "approved_count": 0,
            "flagged_count": 0,
            "blocked_count": 0,
            "error_count": 0,
            "average_check_time": 0.0,
            "total_processing_time": 0.0,
            "min_check_time": float('inf'),
            "max_check_time": 0.0
        }
    
    def update_processing_stats(self, processing_time_ms: float):
        """
        更新处理时间统计
        
        参数:
            processing_time_ms: 处理时间（毫秒）
        """
        self.processing_metrics["total_processing_time"] += processing_time_ms
        
        # 更新最小和最大处理时间
        if processing_time_ms < self.processing_metrics["min_check_time"]:
            self.processing_metrics["min_check_time"] = processing_time_ms
        
        if processing_time_ms > self.processing_metrics["max_check_time"]:
            self.processing_metrics["max_check_time"] = processing_time_ms
        
        # 重新计算平均处理时间
        total_checks = self.processing_metrics["total_checks"]
        if total_checks > 0:
            self.processing_metrics["average_check_time"] = (
                self.processing_metrics["total_processing_time"] / total_checks
            )
    
    def update_status_metrics(self, status: str):
        """
        更新状态统计指标
        
        参数:
            status: 处理状态 (approved/flagged/blocked/error)
        """
        self.processing_metrics["total_checks"] += 1
        
        if status == "approved":
            self.processing_metrics["approved_count"] += 1
        elif status == "flagged":
            self.processing_metrics["flagged_count"] += 1
        elif status == "blocked":
            self.processing_metrics["blocked_count"] += 1
        elif status == "error":
            self.processing_metrics["error_count"] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        返回:
            Dict[str, Any]: 完整的性能统计信息
        """
        uptime_seconds = get_processing_time_ms(self.start_time)
        
        base_stats = self.processing_metrics.copy()
        
        # 添加运行时统计
        base_stats.update({
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": self._format_uptime(uptime_seconds),
            "checks_per_minute": self._calculate_checks_per_minute(uptime_seconds),
            "success_rate": self._calculate_success_rate(),
            "error_rate": self._calculate_error_rate(),
            "compliance_rate": self._calculate_compliance_rate()
        })
        
        return base_stats
    
    def get_compliance_stats(self, rule_set_stats: Dict[str, Any], 
                           audit_log_size: int, is_active: bool) -> Dict[str, Any]:
        """
        获取完整的合规统计信息
        
        参数:
            rule_set_stats: 规则集统计信息
            audit_log_size: 审计日志大小
            is_active: 智能体活跃状态
            
        返回:
            Dict[str, Any]: 完整的合规统计信息
        """
        return {
            "agent_id": self.agent_id,
            "agent_id": self.agent_id,
            "rule_set_stats": rule_set_stats,
            "processing_metrics": self.get_performance_stats(),
            "audit_log_size": audit_log_size,
            "is_active": is_active,
            "last_check": to_isoformat(self.start_time)
        }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """
        格式化运行时间
        
        参数:
            uptime_seconds: 运行时间（秒）
            
        返回:
            str: 格式化的运行时间
        """
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _calculate_checks_per_minute(self, uptime_seconds: float) -> float:
        """
        计算每分钟检查次数
        
        参数:
            uptime_seconds: 运行时间（秒）
            
        返回:
            float: 每分钟检查次数
        """
        if uptime_seconds < 60:
            return 0.0
        
        uptime_minutes = uptime_seconds / 60
        return self.processing_metrics["total_checks"] / uptime_minutes
    
    def _calculate_success_rate(self) -> float:
        """
        计算成功率（非错误状态的比例）
        
        返回:
            float: 成功率百分比
        """
        total_checks = self.processing_metrics["total_checks"]
        if total_checks == 0:
            return 100.0
        
        successful_checks = (
            self.processing_metrics["approved_count"] +
            self.processing_metrics["flagged_count"] +
            self.processing_metrics["blocked_count"]
        )
        
        return (successful_checks / total_checks) * 100
    
    def _calculate_error_rate(self) -> float:
        """
        计算错误率
        
        返回:
            float: 错误率百分比
        """
        total_checks = self.processing_metrics["total_checks"]
        if total_checks == 0:
            return 0.0
        
        return (self.processing_metrics["error_count"] / total_checks) * 100
    
    def _calculate_compliance_rate(self) -> float:
        """
        计算合规率（通过检查的比例）
        
        返回:
            float: 合规率百分比
        """
        total_checks = self.processing_metrics["total_checks"]
        if total_checks == 0:
            return 100.0
        
        return (self.processing_metrics["approved_count"] / total_checks) * 100
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        返回:
            Dict[str, Any]: 健康状态信息
        """
        error_rate = self._calculate_error_rate()
        avg_time = self.processing_metrics["average_check_time"]
        
        # 判断健康状态
        if error_rate > 10:
            health_status = "critical"
        elif error_rate > 5 or avg_time > 2000:  # 2秒阈值
            health_status = "warning"
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "error_rate": error_rate,
            "average_response_time": avg_time,
            "total_checks": self.processing_metrics["total_checks"],
            "uptime_seconds": get_processing_time_ms(self.start_time),
            "timestamp": to_isoformat()
        }
    
    def reset_metrics(self):
        """
        重置所有性能指标
        """
        self.start_time = get_current_datetime()
        self.processing_metrics = {
            "total_checks": 0,
            "approved_count": 0,
            "flagged_count": 0,
            "blocked_count": 0,
            "error_count": 0,
            "average_check_time": 0.0,
            "total_processing_time": 0.0,
            "min_check_time": float('inf'),
            "max_check_time": 0.0
        } 