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
import time
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
    
    # 供应商类型到实现类的映射
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
        
        # 供应商实例存储 {tenant_id: {provider_type: provider_instance}}
        self.providers: Dict[str, Dict[ProviderType, BaseProvider]] = {}
        
        # 默认供应商实例(无租户)
        self.default_providers: Dict[ProviderType, BaseProvider] = {}
        
        # 健康监控
        self.health_check_interval = 300  # 5分钟
        self.health_check_task: Optional[asyncio.Task] = None
        
        # 性能监控
        self.stats_collection_interval = 60  # 1分钟
        self.stats_task: Optional[asyncio.Task] = None
        
        # 线程池用于并发操作
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        self.logger.info("供应商管理器初始化完成")
    
    async def initialize(self):
        """
        初始化所有供应商
        """
        try:
            # 初始化默认供应商
            await self._initialize_default_providers()
            
            # 初始化租户供应商
            await self._initialize_tenant_providers()
            
            # 启动健康监控
            await self._start_health_monitoring()
            
            # 启动性能统计收集
            await self._start_stats_collection()
            
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
                    provider_class = self.PROVIDER_CLASSES.get(provider_enum)
                    
                    if provider_class:
                        provider_instance = provider_class(provider_config)
                        
                        # 测试连接
                        if await provider_instance.test_connection():
                            self.default_providers[provider_enum] = provider_instance
                            self.logger.info(f"默认供应商初始化成功: {provider_type}")
                        else:
                            self.logger.warning(f"默认供应商连接测试失败: {provider_type}")
                    else:
                        self.logger.error(f"未找到供应商实现类: {provider_type}")
                        
            except Exception as e:
                self.logger.error(f"默认供应商初始化失败 {provider_type}: {str(e)}")
    
    async def _initialize_tenant_providers(self):
        """初始化租户供应商"""
        for tenant_id, tenant_config in self.config.tenant_configs.items():
            await self._initialize_tenant_provider(tenant_id, tenant_config)
    
    async def _initialize_tenant_provider(self, tenant_id: str, tenant_config: TenantProviderConfig):
        """
        初始化特定租户的供应商
        
        参数:
            tenant_id: 租户ID
            tenant_config: 租户配置
        """
        tenant_providers = {}
        
        for provider_type, provider_config in tenant_config.provider_configs.items():
            try:
                if provider_config.is_enabled:
                    provider_enum = ProviderType(provider_type)
                    provider_class = self.PROVIDER_CLASSES.get(provider_enum)
                    
                    if provider_class:
                        provider_instance = provider_class(provider_config)
                        
                        # 测试连接
                        if await provider_instance.test_connection():
                            tenant_providers[provider_enum] = provider_instance
                            self.logger.info(f"租户供应商初始化成功: {tenant_id}/{provider_type}")
                        else:
                            self.logger.warning(f"租户供应商连接测试失败: {tenant_id}/{provider_type}")
                    else:
                        self.logger.error(f"未找到供应商实现类: {provider_type}")
                        
            except Exception as e:
                self.logger.error(f"租户供应商初始化失败 {tenant_id}/{provider_type}: {str(e)}")
        
        if tenant_providers:
            self.providers[tenant_id] = tenant_providers
    
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
        if tenant_id and tenant_id in self.providers:
            tenant_provider = self.providers[tenant_id].get(provider_type)
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
        if tenant_id and tenant_id in self.providers:
            for provider in self.providers[tenant_id].values():
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
    
    async def _reinitialize_provider(
        self, 
        provider_type: ProviderType, 
        provider_config: ProviderConfig,
        tenant_id: Optional[str] = None
    ):
        """重新初始化供应商"""
        try:
            provider_class = self.PROVIDER_CLASSES.get(provider_type)
            if not provider_class:
                raise ProviderError(f"未找到供应商实现类: {provider_type}", provider_type, "CLASS_NOT_FOUND")
            
            # 创建新实例
            new_provider = provider_class(provider_config)
            
            # 测试连接
            if await new_provider.test_connection():
                # 替换旧实例
                if tenant_id:
                    if tenant_id not in self.providers:
                        self.providers[tenant_id] = {}
                    self.providers[tenant_id][provider_type] = new_provider
                else:
                    self.default_providers[provider_type] = new_provider
                
                self.logger.info(f"供应商重新初始化成功: {provider_type}/{tenant_id or 'default'}")
            else:
                raise ProviderError(f"供应商连接测试失败: {provider_type}", provider_type, "CONNECTION_FAILED")
                
        except Exception as e:
            self.logger.error(f"供应商重新初始化失败: {str(e)}")
            raise
    
    async def _start_health_monitoring(self):
        """启动健康监控任务"""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.logger.info("健康监控任务启动")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"健康检查循环错误: {str(e)}")
                await asyncio.sleep(60)  # 错误时短暂等待
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        # 检查默认供应商
        for provider_type, provider in self.default_providers.items():
            try:
                health_status = await provider.health_check()
                if not health_status:
                    self.logger.warning(f"默认供应商健康检查失败: {provider_type}")
            except Exception as e:
                self.logger.error(f"默认供应商健康检查异常 {provider_type}: {str(e)}")
        
        # 检查租户供应商
        for tenant_id, tenant_providers in self.providers.items():
            for provider_type, provider in tenant_providers.items():
                try:
                    health_status = await provider.health_check()
                    if not health_status:
                        self.logger.warning(f"租户供应商健康检查失败: {tenant_id}/{provider_type}")
                except Exception as e:
                    self.logger.error(f"租户供应商健康检查异常 {tenant_id}/{provider_type}: {str(e)}")
    
    async def _start_stats_collection(self):
        """启动性能统计收集任务"""
        if self.stats_task is None or self.stats_task.done():
            self.stats_task = asyncio.create_task(self._stats_collection_loop())
            self.logger.info("性能统计收集任务启动")
    
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
            stats_data["default_providers"][provider_type.value] = provider.get_stats()
        
        # 收集租户供应商统计
        for tenant_id, tenant_providers in self.providers.items():
            stats_data["tenant_providers"][tenant_id] = {}
            for provider_type, provider in tenant_providers.items():
                stats_data["tenant_providers"][tenant_id][provider_type.value] = provider.get_stats()
        
        # 这里可以将统计数据发送到监控系统
        self.logger.debug(f"收集到性能统计数据: {len(stats_data['default_providers'])} 个默认供应商, "
                         f"{len(stats_data['tenant_providers'])} 个租户")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        返回:
            Dict[str, Any]: 全局统计数据
        """
        stats = {
            "provider_count": {
                "default": len(self.default_providers),
                "tenant": sum(len(providers) for providers in self.providers.values())
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
                    for tenant_id, tenant_providers in self.providers.items()
                }
            },
            "total_requests": sum(
                provider.stats["total_requests"] 
                for provider in self.default_providers.values()
            ) + sum(
                provider.stats["total_requests"]
                for tenant_providers in self.providers.values()
                for provider in tenant_providers.values()
            )
        }
        
        return stats
    
    async def shutdown(self):
        """关闭供应商管理器"""
        try:
            # 停止健康监控任务
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 停止统计收集任务
            if self.stats_task and not self.stats_task.done():
                self.stats_task.cancel()
                try:
                    await self.stats_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭线程池
            self.executor.shutdown(wait=True)
            
            self.logger.info("供应商管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"供应商管理器关闭错误: {str(e)}")