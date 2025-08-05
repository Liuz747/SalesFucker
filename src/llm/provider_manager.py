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
from concurrent.futures import ThreadPoolExecutor

from .base_provider import BaseProvider, ProviderError
from .provider_config import (
    ProviderType, 
    ProviderConfig, 
    GlobalProviderConfig,
    TenantProviderConfig,
    ProviderHealth
)
from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    DeepSeekProvider
)
from src.utils import get_component_logger, ErrorHandler


class ProviderManager:
    """
    供应商管理器类
    
    负责管理所有LLM供应商的生命周期，包括初始化、配置、
    健康监控和性能统计等功能。
    """
    
    # 供应商类型到实现类的映射 (集成 LifecycleManager 功能)
    PROVIDER_CLASSES: Dict[ProviderType, Type[BaseProvider]] = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.DEEPSEEK: DeepSeekProvider
    }
    
    def __init__(self, config: GlobalProviderConfig):
        """
        初始化供应商管理器
        
        参数:
            config: 全局供应商配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "ProviderManager")
        self.error_handler = ErrorHandler("provider_manager")
        
        # 供应商实例存储 (集成 LifecycleManager 功能)
        self.default_providers: Dict[ProviderType, BaseProvider] = {}
        self.tenant_providers: Dict[str, Dict[ProviderType, BaseProvider]] = {}
        
        # 健康监控配置 (集成 HealthMonitor 功能)
        self.health_check_interval = 300  # 5分钟
        self.health_check_task: Optional[asyncio.Task] = None
        self.health_history: Dict[str, list] = {}
        self.last_check_time: Optional[datetime] = None
        
        # 统计收集配置 (集成 StatsCollector 功能)
        self.stats_collection_interval = 60  # 1分钟
        self.stats_task: Optional[asyncio.Task] = None
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.stats_history: list = []
        self.max_history_records = 1000
        
        self.logger.info("供应商管理器初始化完成")
    
    async def initialize(self):
        """
        初始化所有供应商
        """
        try:
            # 初始化供应商 (集成功能)
            await self._initialize_all_providers()
            
            # 启动监控任务 (集成功能)
            await self._start_monitoring()
            await self._start_collection()
            
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
        # 优先使用租户特定的供应商
        if tenant_id and tenant_id in self.tenant_providers:
            tenant_provider = self.tenant_providers[tenant_id].get(provider_type)
            if tenant_provider and tenant_provider.health.is_healthy:
                return tenant_provider
        
        # 回退到默认供应商
        default_provider = self.default_providers.get(provider_type)
        if default_provider and default_provider.health.is_healthy:
            return default_provider
        
        return None
    
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
        
        # 添加租户特定的供应商
        if tenant_id and tenant_id in self.tenant_providers:
            for provider in self.tenant_providers[tenant_id].values():
                if provider.health.is_healthy:
                    available_providers.append(provider)
        
        # 添加默认供应商(如果租户没有相同类型的供应商)
        used_types = {p.provider_type for p in available_providers}
        for provider_type, provider in self.default_providers.items():
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
        try:
            # 更新配置
            self.config.tenant_configs[tenant_id] = tenant_config
            
            # 初始化租户供应商
            await self._initialize_tenant_provider(tenant_id, tenant_config)
            
            self.logger.info(f"租户配置添加成功: {tenant_id}")
            
        except Exception as e:
            self.logger.error(f"添加租户配置失败 {tenant_id}: {str(e)}")
            raise
    
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
        try:
            # 更新配置
            if tenant_id:
                if tenant_id not in self.config.tenant_configs:
                    self.config.tenant_configs[tenant_id] = TenantProviderConfig(tenant_id=tenant_id)
                self.config.tenant_configs[tenant_id].provider_configs[provider_type.value] = provider_config
            else:
                self.config.default_providers[provider_type.value] = provider_config
            
            # 重新初始化供应商
            await self._reinitialize_provider(provider_type, provider_config, tenant_id)
            
            self.logger.info(f"供应商配置更新成功: {provider_type}/{tenant_id or 'default'}")
            
        except Exception as e:
            self.logger.error(f"更新供应商配置失败 {provider_type}/{tenant_id}: {str(e)}")
            raise
    
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
        base_stats = self._get_global_stats()
        health_summary = self._get_health_summary()
        
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
            "health_summary": self._get_health_summary(),
            "performance_summary": self._get_performance_summary(),
            "unhealthy_providers": self._get_unhealthy_providers()
        }
    
    async def force_health_check(self, provider_type: Optional[str] = None, tenant_id: Optional[str] = None):
        """强制执行健康检查"""
        if provider_type and tenant_id:
            provider_key = f"{tenant_id}_{provider_type}"
        elif provider_type:
            provider_key = f"default_{provider_type}"
        else:
            provider_key = None
        
        await self._force_health_check(provider_key)
    
    async def shutdown(self):
        """关闭供应商管理器"""
        try:
            # 停止监控任务
            await self._stop_monitoring()
            await self._stop_collection()
            
            self.logger.info("供应商管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"供应商管理器关闭错误: {str(e)}")
    
    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        self._clear_health_history(days)
        self._clear_stats_history(days)
        self.logger.info(f"清理了 {days} 天前的历史数据")
    
    # 集成的生命周期管理功能 (原 LifecycleManager)
    async def _initialize_all_providers(self):
        """初始化所有供应商"""
        try:
            # 初始化默认供应商
            await self._initialize_default_providers()
            
            # 初始化租户供应商
            await self._initialize_tenant_providers()
            
            self.logger.info("所有供应商初始化完成")
            
        except Exception as e:
            self.logger.error(f"供应商初始化失败: {str(e)}")
            raise ProviderError(f"供应商管理器初始化失败: {str(e)}", None, "INIT_FAILED")
    
    async def _initialize_default_providers(self):
        """初始化默认供应商"""
        for provider_type, provider_config in self.config.default_providers.items():
            try:
                if provider_config.is_enabled:
                    provider_enum = ProviderType(provider_type)
                    provider_instance = await self._create_provider_instance(
                        provider_enum, provider_config
                    )
                    
                    if provider_instance:
                        self.default_providers[provider_enum] = provider_instance
                        self.logger.info(f"默认供应商初始化成功: {provider_type}")
                    else:
                        self.logger.warning(f"默认供应商初始化失败: {provider_type}")
                        
            except Exception as e:
                self.logger.error(f"默认供应商初始化失败 {provider_type}: {str(e)}")
    
    async def _initialize_tenant_providers(self):
        """初始化租户供应商"""
        for tenant_id, tenant_config in self.config.tenant_configs.items():
            await self._initialize_tenant_provider(tenant_id, tenant_config)
    
    async def _initialize_tenant_provider(self, tenant_id: str, tenant_config: TenantProviderConfig):
        """初始化特定租户的供应商"""
        tenant_providers = {}
        
        for provider_type, provider_config in tenant_config.provider_configs.items():
            try:
                if provider_config.is_enabled:
                    provider_enum = ProviderType(provider_type)
                    provider_instance = await self._create_provider_instance(
                        provider_enum, provider_config
                    )
                    
                    if provider_instance:
                        tenant_providers[provider_enum] = provider_instance
                        self.logger.info(f"租户供应商初始化成功: {tenant_id}/{provider_type}")
                    else:
                        self.logger.warning(f"租户供应商初始化失败: {tenant_id}/{provider_type}")
                        
            except Exception as e:
                self.logger.error(f"租户供应商初始化失败 {tenant_id}/{provider_type}: {str(e)}")
        
        if tenant_providers:
            self.tenant_providers[tenant_id] = tenant_providers
    
    async def _create_provider_instance(
        self, 
        provider_type: ProviderType, 
        provider_config: ProviderConfig
    ) -> Optional[BaseProvider]:
        """创建供应商实例"""
        provider_class = self.PROVIDER_CLASSES.get(provider_type)
        if not provider_class:
            self.logger.error(f"未找到供应商实现类: {provider_type}")
            return None
        
        try:
            provider_instance = provider_class(provider_config)
            
            # 测试连接
            if await provider_instance.test_connection():
                return provider_instance
            else:
                self.logger.warning(f"供应商连接测试失败: {provider_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建供应商实例失败 {provider_type}: {str(e)}")
            return None
    
    async def _reinitialize_provider(
        self, 
        provider_type: ProviderType, 
        provider_config: ProviderConfig,
        tenant_id: Optional[str] = None
    ):
        """重新初始化供应商"""
        try:
            provider_instance = await self._create_provider_instance(provider_type, provider_config)
            
            if provider_instance:
                # 替换旧实例
                if tenant_id:
                    if tenant_id not in self.tenant_providers:
                        self.tenant_providers[tenant_id] = {}
                    self.tenant_providers[tenant_id][provider_type] = provider_instance
                else:
                    self.default_providers[provider_type] = provider_instance
                
                self.logger.info(f"供应商重新初始化成功: {provider_type}/{tenant_id or 'default'}")
            else:
                raise ProviderError(f"供应商连接测试失败: {provider_type}", provider_type, "CONNECTION_FAILED")
                
        except Exception as e:
            self.logger.error(f"供应商重新初始化失败: {str(e)}")
            raise
    
    # 集成的健康监控功能 (原 HealthMonitor)
    async def _start_monitoring(self):
        """启动健康监控任务"""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.logger.info("健康监控任务启动")
    
    async def _stop_monitoring(self):
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
        """检查单个供应商健康状态"""
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
    
    def _get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
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
    
    def _get_unhealthy_providers(self) -> list:
        """获取当前不健康的供应商列表"""
        unhealthy = []
        
        for provider_key, history in self.health_history.items():
            if history and not history[-1]["is_healthy"]:
                unhealthy.append(provider_key)
        
        return unhealthy
    
    async def _force_health_check(self, provider_key: Optional[str] = None):
        """强制执行健康检查"""
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
    
    def _clear_health_history(self, days: int = 7):
        """清理健康历史记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for provider_key in self.health_history:
            self.health_history[provider_key] = [
                h for h in self.health_history[provider_key]
                if datetime.fromisoformat(h["timestamp"]) > cutoff_time
            ]
        
        self.logger.info(f"健康历史记录清理完成，保留 {days} 天数据")
    
    # 集成的统计收集功能 (原 StatsCollector)
    async def _start_collection(self):
        """启动统计收集任务"""
        if self.stats_task is None or self.stats_task.done():
            self.stats_task = asyncio.create_task(self._stats_collection_loop())
            self.logger.info("性能统计收集任务启动")
    
    async def _stop_collection(self):
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
    
    def _get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
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
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要报告"""
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
    
    def _clear_stats_history(self, days: int = 7):
        """清理统计历史记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        self.stats_history = [
            record for record in self.stats_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_time
        ]
        
        self.logger.info(f"统计历史记录清理完成，保留 {days} 天数据，剩余 {len(self.stats_history)} 条记录")