"""
供应商统计收集器模块

该模块负责收集和管理供应商的性能统计数据。
提供统计数据收集、分析和报告功能。

核心功能:
- 性能统计收集
- 使用量监控
- 统计数据分析
- 报告生成
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from ..base_provider import BaseProvider
from ..provider_config import ProviderType
from src.utils import get_component_logger, ErrorHandler


class StatsCollector:
    """
    供应商统计收集器
    
    负责收集和维护供应商的性能统计数据。
    """
    
    def __init__(self, stats_collection_interval: int = 60):
        """
        初始化统计收集器
        
        参数:
            stats_collection_interval: 统计收集间隔（秒）
        """
        self.logger = get_component_logger(__name__, "StatsCollector")
        self.error_handler = ErrorHandler("stats_collector")
        
        # 统计配置
        self.stats_collection_interval = stats_collection_interval
        self.stats_task: Optional[asyncio.Task] = None
        
        # 线程池用于并发操作
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 统计数据存储
        self.stats_history: list = []
        self.max_history_records = 1000
        
        # 供应商引用
        self.default_providers: Dict[ProviderType, BaseProvider] = {}
        self.tenant_providers: Dict[str, Dict[ProviderType, BaseProvider]] = {}
    
    def set_providers(
        self,
        default_providers: Dict[ProviderType, BaseProvider],
        tenant_providers: Dict[str, Dict[ProviderType, BaseProvider]]
    ):
        """设置供应商引用"""
        self.default_providers = default_providers
        self.tenant_providers = tenant_providers
        self.logger.debug("统计收集器供应商引用已设置")
    
    async def start_collection(self):
        """启动统计收集任务"""
        if self.stats_task is None or self.stats_task.done():
            self.stats_task = asyncio.create_task(self._stats_collection_loop())
            self.logger.info("性能统计收集任务启动")
    
    async def stop_collection(self):
        """停止统计收集任务"""
        if self.stats_task and not self.stats_task.done():
            self.stats_task.cancel()
            try:
                await self.stats_task
            except asyncio.CancelledError:
                pass
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        self.logger.info("性能统计收集任务已停止")
    
    async def _stats_collection_loop(self):
        """性能统计收集循环"""
        while True:
            try:
                await self._collect_stats()
                await asyncio.sleep(self.stats_collection_interval)
            except Exception as e:
                self.logger.error(f"性能统计收集错误: {str(e)}")
                await asyncio.sleep(60)
    
    async def _collect_stats(self):
        """收集性能统计数据"""
        stats_data = {
            "timestamp": datetime.now().isoformat(),
            "default_providers": {},
            "tenant_providers": {}
        }
        
        # 收集默认供应商统计
        for provider_type, provider in self.default_providers.items():
            try:
                provider_stats = provider.get_stats()
                stats_data["default_providers"][provider_type.value] = {
                    **provider_stats,
                    "health_status": {
                        "is_healthy": provider.health.is_healthy,
                        "error_rate": provider.health.error_rate,
                        "avg_response_time": provider.health.avg_response_time,
                        "rate_limit_remaining": provider.health.rate_limit_remaining
                    }
                }
            except Exception as e:
                self.logger.error(f"收集默认供应商统计失败 {provider_type}: {str(e)}")
                stats_data["default_providers"][provider_type.value] = {"error": str(e)}
        
        # 收集租户供应商统计
        for tenant_id, tenant_providers in self.tenant_providers.items():
            stats_data["tenant_providers"][tenant_id] = {}
            for provider_type, provider in tenant_providers.items():
                try:
                    provider_stats = provider.get_stats()
                    stats_data["tenant_providers"][tenant_id][provider_type.value] = {
                        **provider_stats,
                        "health_status": {
                            "is_healthy": provider.health.is_healthy,
                            "error_rate": provider.health.error_rate,
                            "avg_response_time": provider.health.avg_response_time,
                            "rate_limit_remaining": provider.health.rate_limit_remaining
                        }
                    }
                except Exception as e:
                    self.logger.error(f"收集租户供应商统计失败 {tenant_id}/{provider_type}: {str(e)}")
                    stats_data["tenant_providers"][tenant_id][provider_type.value] = {"error": str(e)}
        
        # 添加到历史记录
        self.stats_history.append(stats_data)
        
        # 限制历史记录数量
        if len(self.stats_history) > self.max_history_records:
            self.stats_history = self.stats_history[-500:]
        
        self.logger.debug(
            f"收集到性能统计数据: {len(stats_data['default_providers'])} 个默认供应商, "
            f"{len(stats_data['tenant_providers'])} 个租户"
        )
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        返回:
            Dict[str, Any]: 全局统计数据
        """
        stats = {
            "provider_count": {
                "default": len(self.default_providers),
                "tenant": sum(len(providers) for providers in self.tenant_providers.values())
            },
            "health_status": {
                "default": {
                    provider_type.value: provider.health.is_healthy
                    for provider_type, provider in self.default_providers.items()
                },
                "tenant": {
                    tenant_id: {
                        provider_type.value: provider.health.is_healthy
                        for provider_type, provider in tenant_providers.items()
                    }
                    for tenant_id, tenant_providers in self.tenant_providers.items()
                }
            },
            "total_requests": self._calculate_total_requests(),
            "collection_info": {
                "interval_seconds": self.stats_collection_interval,
                "history_records": len(self.stats_history),
                "last_collection": self.stats_history[-1]["timestamp"] if self.stats_history else None
            }
        }
        
        return stats
    
    def _calculate_total_requests(self) -> int:
        """计算总请求数"""
        total = 0
        
        # 默认供应商请求数
        for provider in self.default_providers.values():
            total += provider.stats.get("total_requests", 0)
        
        # 租户供应商请求数
        for tenant_providers in self.tenant_providers.values():
            for provider in tenant_providers.values():
                total += provider.stats.get("total_requests", 0)
        
        return total
    
    def get_provider_stats(
        self, 
        provider_type: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取指定供应商的统计信息
        
        参数:
            provider_type: 供应商类型
            tenant_id: 租户ID
            
        返回:
            Dict[str, Any]: 供应商统计信息
        """
        if tenant_id and tenant_id in self.tenant_providers:
            # 租户供应商
            if provider_type:
                for p_type, provider in self.tenant_providers[tenant_id].items():
                    if p_type.value == provider_type:
                        return provider.get_stats()
            else:
                # 返回租户所有供应商
                return {
                    p_type.value: provider.get_stats()
                    for p_type, provider in self.tenant_providers[tenant_id].items()
                }
        else:
            # 默认供应商
            if provider_type:
                for p_type, provider in self.default_providers.items():
                    if p_type.value == provider_type:
                        return provider.get_stats()
            else:
                # 返回所有默认供应商
                return {
                    p_type.value: provider.get_stats()
                    for p_type, provider in self.default_providers.items()
                }
        
        return {}
    
    def get_stats_trend(
        self, 
        hours: int = 24,
        provider_type: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> list:
        """
        获取统计趋势数据
        
        参数:
            hours: 时间范围（小时）
            provider_type: 供应商类型过滤
            tenant_id: 租户ID过滤
            
        返回:
            list: 趋势数据
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_history = [
            record for record in self.stats_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_time
        ]
        
        if not filtered_history:
            return []
        
        # 提取指定供应商的数据
        trend_data = []
        for record in filtered_history:
            timestamp = record["timestamp"]
            
            if tenant_id and provider_type:
                # 特定租户的特定供应商
                data = record["tenant_providers"].get(tenant_id, {}).get(provider_type, {})
            elif provider_type:
                # 默认供应商中的特定类型
                data = record["default_providers"].get(provider_type, {})
            elif tenant_id:
                # 特定租户的所有供应商
                data = record["tenant_providers"].get(tenant_id, {})
            else:
                # 所有数据
                data = record
            
            if data:
                trend_data.append({
                    "timestamp": timestamp,
                    "data": data
                })
        
        return trend_data
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要报告
        
        返回:
            Dict[str, Any]: 性能摘要
        """
        if not self.stats_history:
            return {"error": "没有统计数据"}
        
        latest_stats = self.stats_history[-1]
        
        summary = {
            "report_time": datetime.now().isoformat(),
            "data_period": {
                "start": self.stats_history[0]["timestamp"],
                "end": latest_stats["timestamp"],
                "total_records": len(self.stats_history)
            },
            "provider_performance": {},
            "tenant_performance": {},
            "overall_metrics": {}
        }
        
        # 默认供应商性能
        for provider_type, stats in latest_stats["default_providers"].items():
            if "error" not in stats:
                summary["provider_performance"][provider_type] = {
                    "total_requests": stats.get("total_requests", 0),
                    "avg_response_time": stats.get("health_status", {}).get("avg_response_time", 0),
                    "error_rate": stats.get("health_status", {}).get("error_rate", 0),
                    "is_healthy": stats.get("health_status", {}).get("is_healthy", False)
                }
        
        # 租户供应商性能
        for tenant_id, tenant_stats in latest_stats["tenant_providers"].items():
            summary["tenant_performance"][tenant_id] = {}
            for provider_type, stats in tenant_stats.items():
                if "error" not in stats:
                    summary["tenant_performance"][tenant_id][provider_type] = {
                        "total_requests": stats.get("total_requests", 0),
                        "avg_response_time": stats.get("health_status", {}).get("avg_response_time", 0),
                        "error_rate": stats.get("health_status", {}).get("error_rate", 0),
                        "is_healthy": stats.get("health_status", {}).get("is_healthy", False)
                    }
        
        # 整体指标
        summary["overall_metrics"] = {
            "total_providers": len(self.default_providers) + sum(len(tp) for tp in self.tenant_providers.values()),
            "healthy_providers": self._count_healthy_providers(),
            "total_requests": self._calculate_total_requests(),
            "collection_active": self.stats_task is not None and not self.stats_task.done()
        }
        
        return summary
    
    def _count_healthy_providers(self) -> int:
        """计算健康供应商数量"""
        count = 0
        
        # 默认供应商
        for provider in self.default_providers.values():
            if provider.health.is_healthy:
                count += 1
        
        # 租户供应商
        for tenant_providers in self.tenant_providers.values():
            for provider in tenant_providers.values():
                if provider.health.is_healthy:
                    count += 1
        
        return count
    
    def clear_stats_history(self, days: int = 7):
        """
        清理统计历史记录
        
        参数:
            days: 保留天数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        self.stats_history = [
            record for record in self.stats_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_time
        ]
        
        self.logger.info(f"统计历史记录清理完成，保留 {days} 天数据，剩余 {len(self.stats_history)} 条记录")