"""
健康监控器模块

该模块负责监控供应商的健康状态，执行定期健康检查。
提供自动故障检测和恢复机制。

核心功能:
- 定期健康检查
- 故障检测和告警
- 健康状态统计
- 自动恢复尝试
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..base_provider import BaseProvider
from ..provider_config import ProviderType
from src.utils import get_component_logger, ErrorHandler


class HealthMonitor:
    """
    健康监控器
    
    负责监控所有供应商的健康状态和性能指标。
    """
    
    def __init__(self, health_check_interval: int = 300):
        """
        初始化健康监控器
        
        参数:
            health_check_interval: 健康检查间隔（秒）
        """
        self.logger = get_component_logger(__name__, "HealthMonitor")
        self.error_handler = ErrorHandler("health_monitor")
        
        # 监控配置
        self.health_check_interval = health_check_interval
        self.health_check_task: Optional[asyncio.Task] = None
        
        # 健康状态记录
        self.health_history: Dict[str, list] = {}
        self.last_check_time: Optional[datetime] = None
        
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
        self.logger.debug("健康监控器供应商引用已设置")
    
    async def start_monitoring(self):
        """启动健康监控任务"""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.logger.info("健康监控任务启动")
    
    async def stop_monitoring(self):
        """停止健康监控任务"""
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.logger.info("健康监控任务已停止")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await self._perform_health_checks()
                self.last_check_time = datetime.now()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"健康检查循环错误: {str(e)}")
                await asyncio.sleep(60)  # 错误时短暂等待
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        # 检查默认供应商
        for provider_type, provider in self.default_providers.items():
            await self._check_provider_health(
                provider, f"default_{provider_type.value}"
            )
        
        # 检查租户供应商
        for tenant_id, tenant_providers in self.tenant_providers.items():
            for provider_type, provider in tenant_providers.items():
                await self._check_provider_health(
                    provider, f"{tenant_id}_{provider_type.value}"
                )
    
    async def _check_provider_health(self, provider: BaseProvider, provider_key: str):
        """
        检查单个供应商健康状态
        
        参数:
            provider: 供应商实例
            provider_key: 供应商标识键
        """
        try:
            start_time = datetime.now()
            health_status = await provider.health_check()
            check_duration = (datetime.now() - start_time).total_seconds()
            
            # 记录健康状态历史
            health_record = {
                "timestamp": start_time.isoformat(),
                "is_healthy": health_status,
                "check_duration": check_duration,
                "error_rate": provider.health.error_rate,
                "avg_response_time": provider.health.avg_response_time
            }
            
            if provider_key not in self.health_history:
                self.health_history[provider_key] = []
            
            self.health_history[provider_key].append(health_record)
            
            # 保持历史记录数量限制
            if len(self.health_history[provider_key]) > 100:
                self.health_history[provider_key] = self.health_history[provider_key][-50:]
            
            if not health_status:
                self.logger.warning(f"供应商健康检查失败: {provider_key}")
            else:
                self.logger.debug(f"供应商健康检查通过: {provider_key}")
                
        except Exception as e:
            self.logger.error(f"供应商健康检查异常 {provider_key}: {str(e)}")
            self.error_handler.handle_error(e, {"provider_key": provider_key})
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        获取健康状态摘要
        
        返回:
            Dict[str, Any]: 健康状态摘要
        """
        summary = {
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "check_interval_seconds": self.health_check_interval,
            "monitoring_active": self.health_check_task is not None and not self.health_check_task.done(),
            "provider_health": {}
        }
        
        # 汇总各供应商的健康状态
        for provider_key, history in self.health_history.items():
            if history:
                latest_check = history[-1]
                recent_checks = [
                    h for h in history[-10:] 
                    if datetime.fromisoformat(h["timestamp"]) > datetime.now() - timedelta(hours=1)
                ]
                
                summary["provider_health"][provider_key] = {
                    "current_status": "healthy" if latest_check["is_healthy"] else "unhealthy",
                    "last_check": latest_check["timestamp"],
                    "recent_success_rate": sum(1 for h in recent_checks if h["is_healthy"]) / len(recent_checks) if recent_checks else 0,
                    "avg_check_duration": sum(h["check_duration"] for h in recent_checks) / len(recent_checks) if recent_checks else 0,
                    "error_rate": latest_check["error_rate"],
                    "avg_response_time": latest_check["avg_response_time"]
                }
        
        return summary
    
    def get_provider_health_history(
        self, 
        provider_key: str, 
        hours: int = 24
    ) -> list:
        """
        获取指定供应商的健康历史
        
        参数:
            provider_key: 供应商标识键
            hours: 历史时间范围（小时）
            
        返回:
            list: 健康历史记录
        """
        if provider_key not in self.health_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            h for h in self.health_history[provider_key]
            if datetime.fromisoformat(h["timestamp"]) > cutoff_time
        ]
    
    def get_unhealthy_providers(self) -> list:
        """
        获取当前不健康的供应商列表
        
        返回:
            list: 不健康的供应商标识键列表
        """
        unhealthy = []
        
        for provider_key, history in self.health_history.items():
            if history and not history[-1]["is_healthy"]:
                unhealthy.append(provider_key)
        
        return unhealthy
    
    async def force_health_check(self, provider_key: Optional[str] = None):
        """
        强制执行健康检查
        
        参数:
            provider_key: 指定供应商标识键，None表示检查所有
        """
        if provider_key:
            # 检查指定供应商
            if provider_key.startswith("default_"):
                provider_type_str = provider_key.replace("default_", "")
                for provider_type, provider in self.default_providers.items():
                    if provider_type.value == provider_type_str:
                        await self._check_provider_health(provider, provider_key)
                        break
            else:
                # 租户供应商
                parts = provider_key.split("_", 1)
                if len(parts) == 2:
                    tenant_id, provider_type_str = parts
                    if tenant_id in self.tenant_providers:
                        for provider_type, provider in self.tenant_providers[tenant_id].items():
                            if provider_type.value == provider_type_str:
                                await self._check_provider_health(provider, provider_key)
                                break
        else:
            # 检查所有供应商
            await self._perform_health_checks()
        
        self.logger.info(f"强制健康检查完成: {provider_key or 'all'}")
    
    def clear_health_history(self, days: int = 7):
        """
        清理健康历史记录
        
        参数:
            days: 保留天数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for provider_key in self.health_history:
            self.health_history[provider_key] = [
                h for h in self.health_history[provider_key]
                if datetime.fromisoformat(h["timestamp"]) > cutoff_time
            ]
        
        self.logger.info(f"健康历史记录清理完成，保留 {days} 天数据")