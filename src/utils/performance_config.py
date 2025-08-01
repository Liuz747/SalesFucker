"""
性能配置模块

集中管理所有性能相关的配置和优化策略。
为生产环境提供可调整的性能参数。

核心功能:
- 数据库连接池配置
- 缓存策略配置
- 并发处理配置
- 监控阈值配置
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class PerformanceLevel(Enum):
    """性能级别枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    HIGH_LOAD = "high_load"


@dataclass
class DatabaseConfig:
    """数据库性能配置"""
    # Elasticsearch配置
    es_connection_pool_size: int = 20
    es_timeout: int = 30
    es_retry_attempts: int = 3
    es_bulk_size: int = 100
    es_refresh_interval: str = "5s"
    
    # Redis配置
    redis_connection_pool_size: int = 50
    redis_timeout: int = 5
    redis_retry_attempts: int = 3
    redis_max_connections_per_pool: int = 100
    
    # 连接复用配置
    connection_keepalive: bool = True
    connection_max_idle_time: int = 300  # 5分钟


@dataclass
class CacheConfig:
    """缓存性能配置"""
    # 多级缓存配置
    local_cache_size: int = 1000
    local_cache_ttl: int = 300  # 5分钟
    
    redis_cache_ttl: int = 3600  # 1小时
    redis_cache_compression: bool = True
    
    # 缓存策略
    cache_hit_logging: bool = False
    cache_warmup_enabled: bool = True
    cache_prefetch_enabled: bool = True
    
    # 内存管理
    memory_threshold_warning: float = 0.8  # 80%
    memory_threshold_critical: float = 0.9  # 90%
    gc_threshold: int = 1000  # 对象数量


@dataclass
class ConcurrencyConfig:
    """并发处理配置"""
    # 异步处理配置
    max_concurrent_agents: int = 5
    max_concurrent_requests: int = 100
    agent_timeout: int = 10000  # 10秒
    
    # 线程池配置
    thread_pool_workers: int = 4
    io_thread_pool_workers: int = 8
    
    # 队列配置
    max_queue_size: int = 1000
    queue_timeout: int = 30
    
    # 批处理配置
    batch_size: int = 50
    batch_timeout: int = 5000  # 5秒
    batch_max_wait: int = 1000  # 1秒


@dataclass
class MonitoringConfig:
    """监控和告警配置"""
    # 性能阈值
    response_time_warning: int = 1000  # 1秒
    response_time_critical: int = 5000  # 5秒
    
    error_rate_warning: float = 5.0  # 5%
    error_rate_critical: float = 10.0  # 10%
    
    memory_usage_warning: float = 70.0  # 70%
    memory_usage_critical: float = 85.0  # 85%
    
    # 监控采样
    metrics_sampling_rate: float = 1.0  # 100%
    detailed_logging: bool = False
    performance_profiling: bool = False
    
    # 健康检查
    health_check_interval: int = 30  # 30秒
    health_check_timeout: int = 5  # 5秒


class PerformanceConfigManager:
    """性能配置管理器"""
    
    def __init__(self, performance_level: PerformanceLevel = PerformanceLevel.DEVELOPMENT):
        self.performance_level = performance_level
        self._configs = self._init_configs()
    
    def _init_configs(self) -> Dict[str, Any]:
        """根据性能级别初始化配置"""
        base_configs = {
            "database": DatabaseConfig(),
            "cache": CacheConfig(),
            "concurrency": ConcurrencyConfig(),
            "monitoring": MonitoringConfig()
        }
        
        # 根据性能级别调整配置
        if self.performance_level == PerformanceLevel.PRODUCTION:
            self._apply_production_config(base_configs)
        elif self.performance_level == PerformanceLevel.HIGH_LOAD:
            self._apply_high_load_config(base_configs)
        elif self.performance_level == PerformanceLevel.TESTING:
            self._apply_testing_config(base_configs)
        
        return base_configs
    
    def _apply_production_config(self, configs: Dict[str, Any]):
        """应用生产环境配置"""
        # 数据库优化
        configs["database"].es_connection_pool_size = 50
        configs["database"].redis_connection_pool_size = 100
        configs["database"].es_bulk_size = 200
        
        # 缓存优化
        configs["cache"].local_cache_size = 5000
        configs["cache"].cache_warmup_enabled = True
        configs["cache"].cache_prefetch_enabled = True
        
        # 并发优化
        configs["concurrency"].max_concurrent_agents = 10
        configs["concurrency"].max_concurrent_requests = 500
        configs["concurrency"].thread_pool_workers = 8
        
        # 监控优化
        configs["monitoring"].detailed_logging = True
        configs["monitoring"].performance_profiling = True
    
    def _apply_high_load_config(self, configs: Dict[str, Any]):
        """应用高负载环境配置"""
        # 极限性能配置
        configs["database"].es_connection_pool_size = 100
        configs["database"].redis_connection_pool_size = 200
        configs["database"].es_bulk_size = 500
        
        configs["cache"].local_cache_size = 10000
        configs["cache"].redis_cache_compression = True
        
        configs["concurrency"].max_concurrent_agents = 20
        configs["concurrency"].max_concurrent_requests = 1000
        configs["concurrency"].thread_pool_workers = 16
        configs["concurrency"].batch_size = 100
        
        # 更严格的监控
        configs["monitoring"].response_time_warning = 500
        configs["monitoring"].error_rate_warning = 2.0
    
    def _apply_testing_config(self, configs: Dict[str, Any]):
        """应用测试环境配置"""
        # 最小资源配置
        configs["database"].es_connection_pool_size = 5
        configs["database"].redis_connection_pool_size = 10
        
        configs["cache"].local_cache_size = 100
        configs["cache"].cache_warmup_enabled = False
        
        configs["concurrency"].max_concurrent_agents = 2
        configs["concurrency"].max_concurrent_requests = 20
        configs["concurrency"].thread_pool_workers = 2
        
        # 详细监控用于调试
        configs["monitoring"].detailed_logging = True
        configs["monitoring"].metrics_sampling_rate = 1.0
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self._configs["database"]
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        return self._configs["cache"]
    
    def get_concurrency_config(self) -> ConcurrencyConfig:
        """获取并发配置"""
        return self._configs["concurrency"]
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """获取监控配置"""
        return self._configs["monitoring"]
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._configs.copy()
    
    def update_config(self, config_type: str, updates: Dict[str, Any]):
        """动态更新配置"""
        if config_type in self._configs:
            config_obj = self._configs[config_type]
            for key, value in updates.items():
                if hasattr(config_obj, key):
                    setattr(config_obj, key, value)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能配置摘要"""
        db_config = self.get_database_config()
        cache_config = self.get_cache_config()
        concurrency_config = self.get_concurrency_config()
        
        return {
            "performance_level": self.performance_level.value,
            "expected_throughput": {
                "max_concurrent_requests": concurrency_config.max_concurrent_requests,
                "max_concurrent_agents": concurrency_config.max_concurrent_agents,
                "batch_processing_capacity": concurrency_config.batch_size * 20  # 每秒批次估算
            },
            "memory_optimization": {
                "local_cache_size": cache_config.local_cache_size,
                "connection_pooling": db_config.es_connection_pool_size + db_config.redis_connection_pool_size,
                "estimated_memory_usage_mb": self._estimate_memory_usage()
            },
            "latency_targets": {
                "memory_retrieval_ms": 50,
                "product_recommendation_ms": 300,
                "full_conversation_ms": 1500,
                "cache_hit_latency_ms": 1
            },
            "scalability_metrics": {
                "concurrent_users_supported": concurrency_config.max_concurrent_requests,
                "database_tps": db_config.es_bulk_size * 10,  # 估算
                "cache_ops_per_second": 10000
            }
        }
    
    def _estimate_memory_usage(self) -> int:
        """估算内存使用量（MB）"""
        cache_config = self.get_cache_config()
        db_config = self.get_database_config()
        
        # 粗略估算
        local_cache_mb = cache_config.local_cache_size * 0.001  # 每个条目约1KB
        connection_pool_mb = (db_config.es_connection_pool_size + db_config.redis_connection_pool_size) * 0.1
        base_app_mb = 100  # 基础应用内存
        
        return int(local_cache_mb + connection_pool_mb + base_app_mb)


# 全局性能配置实例
def get_performance_config(level: PerformanceLevel = PerformanceLevel.DEVELOPMENT) -> PerformanceConfigManager:
    """获取性能配置实例"""
    return PerformanceConfigManager(level)


# 快速配置函数
def get_production_config() -> PerformanceConfigManager:
    """获取生产环境配置"""
    return get_performance_config(PerformanceLevel.PRODUCTION)


def get_high_load_config() -> PerformanceConfigManager:
    """获取高负载环境配置"""
    return get_performance_config(PerformanceLevel.HIGH_LOAD)


def get_testing_config() -> PerformanceConfigManager:
    """获取测试环境配置"""
    return get_performance_config(PerformanceLevel.TESTING)