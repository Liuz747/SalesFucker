"""
性能监控模块

提供高性能存储系统的性能监控和统计分析。
实时跟踪缓存命中率、查询性能和系统资源使用情况。

核心功能:
- 实时性能统计
- 缓存命中率监控
- 操作延迟跟踪
- 性能报告生成
"""

import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from utils import get_component_logger


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    cache_hits: int = 0
    cache_misses: int = 0
    elasticsearch_queries: int = 0
    redis_operations: int = 0
    batch_writes: int = 0
    total_requests: int = 0
    
    # 延迟统计
    query_latencies: List[float] = field(default_factory=list)
    cache_latencies: List[float] = field(default_factory=list)
    
    # 时间戳
    last_updated: datetime = field(default_factory=datetime.utcnow)


class PerformanceMonitor:
    """
    性能监控器
    
    负责收集和分析高性能存储系统的性能指标，
    提供实时监控和历史趋势分析。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        
        # 历史数据 (保持最近24小时)
        self._history: List[PerformanceMetrics] = []
        self._max_history_size = 24 * 60  # 24小时，每分钟一个快照
    
    def record_cache_hit(self, latency_ms: float = None):
        """记录缓存命中"""
        self.metrics.cache_hits += 1
        self.metrics.total_requests += 1
        
        if latency_ms is not None:
            self.metrics.cache_latencies.append(latency_ms)
        
        self._update_timestamp()
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics.cache_misses += 1
        self.metrics.total_requests += 1
        self._update_timestamp()
    
    def record_elasticsearch_query(self, latency_ms: float = None):
        """记录Elasticsearch查询"""
        self.metrics.elasticsearch_queries += 1
        
        if latency_ms is not None:
            self.metrics.query_latencies.append(latency_ms)
        
        self._update_timestamp()
    
    def record_redis_operation(self):
        """记录Redis操作"""
        self.metrics.redis_operations += 1
        self._update_timestamp()
    
    def record_batch_write(self):
        """记录批量写入"""
        self.metrics.batch_writes += 1
        self._update_timestamp()
    
    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前性能统计"""
        cache_hit_rate = self._calculate_cache_hit_rate()
        avg_query_latency = self._calculate_average_latency(self.metrics.query_latencies)
        avg_cache_latency = self._calculate_average_latency(self.metrics.cache_latencies)
        
        return {
            "tenant_id": self.tenant_id,
            "timestamp": self.metrics.last_updated.isoformat(),
            
            # 缓存指标
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "total_requests": self.metrics.total_requests,
            
            # 操作指标
            "elasticsearch_queries": self.metrics.elasticsearch_queries,
            "redis_operations": self.metrics.redis_operations,
            "batch_writes": self.metrics.batch_writes,
            
            # 延迟指标
            "average_query_latency_ms": avg_query_latency,
            "average_cache_latency_ms": avg_cache_latency,
            
            # 性能评估
            "performance_grade": self._calculate_performance_grade(cache_hit_rate, avg_query_latency)
        }
    
    def get_historical_trends(self, hours: int = 1) -> Dict[str, Any]:
        """获取历史趋势数据"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_history = [
            snapshot for snapshot in self._history 
            if snapshot.last_updated >= cutoff_time
        ]
        
        if not recent_history:
            return {"message": "暂无历史数据"}
        
        # 计算趋势指标
        hit_rates = [self._calculate_cache_hit_rate(snapshot) for snapshot in recent_history]
        query_counts = [snapshot.elasticsearch_queries for snapshot in recent_history]
        
        return {
            "time_range_hours": hours,
            "data_points": len(recent_history),
            "cache_hit_rate_trend": {
                "min": min(hit_rates) if hit_rates else 0,
                "max": max(hit_rates) if hit_rates else 0,
                "avg": sum(hit_rates) / len(hit_rates) if hit_rates else 0
            },
            "query_volume_trend": {
                "min": min(query_counts) if query_counts else 0,
                "max": max(query_counts) if query_counts else 0,
                "total": sum(query_counts) if query_counts else 0
            }
        }
    
    def take_snapshot(self):
        """拍摄当前指标快照并保存到历史记录"""
        # 创建当前状态的快照
        snapshot = PerformanceMetrics(
            cache_hits=self.metrics.cache_hits,
            cache_misses=self.metrics.cache_misses,
            elasticsearch_queries=self.metrics.elasticsearch_queries,
            redis_operations=self.metrics.redis_operations,
            batch_writes=self.metrics.batch_writes,
            total_requests=self.metrics.total_requests,
            query_latencies=self.metrics.query_latencies.copy(),
            cache_latencies=self.metrics.cache_latencies.copy(),
            last_updated=datetime.utcnow()
        )
        
        self._history.append(snapshot)
        
        # 保持历史记录在限制内
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]
        
        # 清理当前延迟记录(避免内存泄漏)
        self.metrics.query_latencies.clear()
        self.metrics.cache_latencies.clear()
    
    def reset_metrics(self):
        """重置性能指标"""
        self.metrics = PerformanceMetrics()
        self.logger.info(f"性能指标已重置: {self.tenant_id}")
    
    def _calculate_cache_hit_rate(self, metrics: PerformanceMetrics = None) -> float:
        """计算缓存命中率"""
        if metrics is None:
            metrics = self.metrics
        
        total = metrics.cache_hits + metrics.cache_misses
        if total == 0:
            return 0.0
        return (metrics.cache_hits / total) * 100
    
    def _calculate_average_latency(self, latencies: List[float]) -> float:
        """计算平均延迟"""
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)
    
    def _calculate_performance_grade(self, cache_hit_rate: float, avg_latency: float) -> str:
        """计算性能等级"""
        # 根据缓存命中率和延迟评估性能
        if cache_hit_rate >= 90 and avg_latency <= 50:
            return "A+"  # 优秀
        elif cache_hit_rate >= 80 and avg_latency <= 100:
            return "A"   # 良好
        elif cache_hit_rate >= 70 and avg_latency <= 200:
            return "B"   # 一般
        elif cache_hit_rate >= 50 and avg_latency <= 500:
            return "C"   # 较差
        else:
            return "D"   # 需要优化
    
    def _update_timestamp(self):
        """更新最后修改时间"""
        self.metrics.last_updated = datetime.utcnow()
    
    def get_summary_report(self) -> Dict[str, Any]:
        """生成性能总结报告"""
        current_stats = self.get_current_stats()
        historical_trends = self.get_historical_trends(hours=24)
        
        return {
            "tenant_id": self.tenant_id,
            "report_time": datetime.utcnow().isoformat(),
            "current_performance": current_stats,
            "24h_trends": historical_trends,
            "recommendations": self._generate_recommendations(current_stats)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        cache_hit_rate = stats.get("cache_hit_rate", 0)
        avg_query_latency = stats.get("average_query_latency_ms", 0)
        
        if cache_hit_rate < 70:
            recommendations.append("缓存命中率较低，建议增加缓存容量或优化缓存策略")
        
        if avg_query_latency > 100:
            recommendations.append("Elasticsearch查询延迟较高，建议优化索引或查询条件")
        
        if stats.get("elasticsearch_queries", 0) > stats.get("cache_hits", 0):
            recommendations.append("数据库查询次数较多，建议优化缓存命中策略")
        
        if not recommendations:
            recommendations.append("性能表现良好，继续保持")
        
        return recommendations
