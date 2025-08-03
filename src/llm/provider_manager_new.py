"""
供应商管理器模块

该模块实现了多LLM供应商的生命周期管理、配置管理和协调功能。
负责供应商的注册、初始化、健康监控和动态配置更新。

核心功能:
- 供应商注册和生命周期管理
- 配置加载和验证
- 健康状态监控和自动恢复
- 多租户隔离和配置管理
- 性能统计和监控数据收集
"""

from typing import Dict, Any, Optional, List, Type
import asyncio
from datetime import datetime, timedelta

from .base_provider import BaseProvider, ProviderError
from .provider_config import (
    ProviderType, 
    ProviderConfig, 
    GlobalProviderConfig,
    TenantProviderConfig,
    ProviderHealth
)
from .provider_manager.lifecycle_manager import LifecycleManager
from .provider_manager.health_monitor import HealthMonitor
from .provider_manager.stats_collector import StatsCollector
from src.utils import get_component_logger, ErrorHandler


class ProviderManager:
    """
    供应商管理器类
    
    负责管理所有LLM供应商的生命周期，包括初始化、配置、
    健康监控和性能统计等功能。
    """
    
    def __init__(self, config: GlobalProviderConfig):
        """
        初始化供应商管理器
        
        参数:
            config: 全局供应商配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "ProviderManager")
        self.error_handler = ErrorHandler("provider_manager")
        
        # 核心组件
        self.lifecycle_manager = LifecycleManager(config)
        self.health_monitor = HealthMonitor()
        self.stats_collector = StatsCollector()
        
        self.logger.info("供应商管理器初始化完成")
    
    async def initialize(self):
        """
        初始化所有供应商
        """
        try:
            # 初始化供应商
            await self.lifecycle_manager.initialize_all_providers()
            
            # 设置监控器的供应商引用
            providers_data = self.lifecycle_manager.get_all_providers()
            self.health_monitor.set_providers(
                providers_data["default"],
                providers_data["tenants"]
            )
            self.stats_collector.set_providers(
                providers_data["default"],
                providers_data["tenants"]
            )
            
            # 启动监控任务
            await self.health_monitor.start_monitoring()
            await self.stats_collector.start_collection()
            
            self.logger.info("所有供应商初始化完成")
            
        except Exception as e:
            self.logger.error(f"供应商初始化失败: {str(e)}")
            raise ProviderError(f"供应商管理器初始化失败: {str(e)}", None, "INIT_FAILED")
    
    def get_provider(
        self, 
        provider_type: ProviderType, 
        tenant_id: Optional[str] = None
    ) -> Optional[BaseProvider]:
        """
        获取指定的供应商实例
        
        参数:
            provider_type: 供应商类型
            tenant_id: 租户ID，可选
            
        返回:
            BaseProvider: 供应商实例或None
        """
        return self.lifecycle_manager.get_provider(provider_type, tenant_id)
    
    def get_available_providers(
        self, 
        tenant_id: Optional[str] = None
    ) -> List[BaseProvider]:
        """
        获取所有可用的供应商实例
        
        参数:
            tenant_id: 租户ID，可选
            
        返回:
            List[BaseProvider]: 可用的供应商列表
        """
        available_providers = []
        providers_data = self.lifecycle_manager.get_all_providers()
        
        # 添加租户特定的供应商
        if tenant_id and tenant_id in providers_data["tenants"]:
            for provider in providers_data["tenants"][tenant_id].values():
                if provider.health.is_healthy:
                    available_providers.append(provider)
        
        # 添加默认供应商(如果租户没有相同类型的供应商)
        used_types = {p.provider_type for p in available_providers}
        for provider_type, provider in providers_data["default"].items():
            if provider_type not in used_types and provider.health.is_healthy:
                available_providers.append(provider)
        
        # 按优先级排序
        available_providers.sort(key=lambda p: p.config.priority)
        
        return available_providers
    
    async def add_tenant_config(self, tenant_id: str, tenant_config: TenantProviderConfig):
        """
        添加新的租户配置
        
        参数:
            tenant_id: 租户ID
            tenant_config: 租户配置
        """
        await self.lifecycle_manager.add_tenant_config(tenant_id, tenant_config)
        
        # 更新监控器引用
        await self._update_monitor_references()
    
    async def update_provider_config(
        self, 
        provider_type: ProviderType, 
        provider_config: ProviderConfig,
        tenant_id: Optional[str] = None
    ):
        """
        更新供应商配置
        
        参数:
            provider_type: 供应商类型
            provider_config: 新的供应商配置
            tenant_id: 租户ID，可选
        """
        await self.lifecycle_manager.update_provider_config(
            provider_type, provider_config, tenant_id
        )
        
        # 更新监控器引用
        await self._update_monitor_references()
    
    async def _update_monitor_references(self):
        """更新监控器的供应商引用"""
        providers_data = self.lifecycle_manager.get_all_providers()
        self.health_monitor.set_providers(
            providers_data["default"],
            providers_data["tenants"]
        )
        self.stats_collector.set_providers(
            providers_data["default"],
            providers_data["tenants"]
        )
    
    async def get_provider_status(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取供应商状态"""
        available_providers = self.get_available_providers(tenant_id)
        
        provider_status = {}
        for provider in available_providers:
            provider_status[provider.provider_type.value] = {
                "is_healthy": provider.health.is_healthy,
                "avg_response_time": provider.health.avg_response_time,
                "error_rate": provider.health.error_rate,
                "rate_limit_remaining": provider.health.rate_limit_remaining,
                "last_check": provider.health.last_check.isoformat(),
                "stats": provider.get_stats()
            }
        
        return provider_status
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        返回:
            Dict[str, Any]: 全局统计数据
        """
        base_stats = self.stats_collector.get_global_stats()
        health_summary = self.health_monitor.get_health_summary()
        
        return {
            **base_stats,
            "health_monitoring": health_summary,
            "manager_info": {
                "initialized": True,
                "config_tenants": len(self.config.tenant_configs),
                "config_default_providers": len(self.config.default_providers)
            }
        }
    
    async def get_health_report(self) -> Dict[str, Any]:
        """获取详细健康报告"""
        return {
            "health_summary": self.health_monitor.get_health_summary(),
            "performance_summary": self.stats_collector.get_performance_summary(),
            "unhealthy_providers": self.health_monitor.get_unhealthy_providers()
        }
    
    async def force_health_check(self, provider_type: Optional[str] = None, tenant_id: Optional[str] = None):
        """强制执行健康检查"""
        if provider_type and tenant_id:
            provider_key = f"{tenant_id}_{provider_type}"
        elif provider_type:
            provider_key = f"default_{provider_type}"
        else:
            provider_key = None
        
        await self.health_monitor.force_health_check(provider_key)
    
    async def shutdown(self):
        """关闭供应商管理器"""
        try:
            # 停止监控任务
            await self.health_monitor.stop_monitoring()
            await self.stats_collector.stop_collection()
            
            self.logger.info("供应商管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"供应商管理器关闭错误: {str(e)}")
    
    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        self.health_monitor.clear_health_history(days)
        self.stats_collector.clear_stats_history(days)
        self.logger.info(f"清理了 {days} 天前的历史数据")