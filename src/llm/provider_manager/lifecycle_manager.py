"""
供应商生命周期管理器模块

该模块负责管理供应商的初始化、配置更新和关闭流程。
提供统一的生命周期管理接口。

核心功能:
- 供应商初始化和连接测试
- 配置更新和重新初始化
- 租户供应商管理
- 健康监控启动
"""

import asyncio
from typing import Dict, Any, Optional, Type
from datetime import datetime

from ..base_provider import BaseProvider, ProviderError
from ..provider_config import (
    ProviderType, 
    ProviderConfig, 
    GlobalProviderConfig,
    TenantProviderConfig
)
from ..providers import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    DeepSeekProvider
)
from src.utils import get_component_logger, ErrorHandler


class LifecycleManager:
    """
    供应商生命周期管理器
    
    负责供应商的初始化、配置更新和生命周期管理。
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
        初始化生命周期管理器
        
        参数:
            config: 全局供应商配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "LifecycleManager")
        self.error_handler = ErrorHandler("lifecycle_manager")
        
        # 供应商实例存储
        self.default_providers: Dict[ProviderType, BaseProvider] = {}
        self.tenant_providers: Dict[str, Dict[ProviderType, BaseProvider]] = {}
    
    async def initialize_all_providers(self):
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
        """
        创建供应商实例
        
        参数:
            provider_type: 供应商类型
            provider_config: 供应商配置
            
        返回:
            Optional[BaseProvider]: 供应商实例或None
        """
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
    
    def get_all_providers(self) -> Dict[str, Any]:
        """获取所有供应商实例"""
        return {
            "default": self.default_providers,
            "tenants": self.tenant_providers
        }