"""
配置管理器模块

该模块提供多LLM供应商配置的安全存储、加载和管理功能。
支持配置加密、验证和热更新等高级功能。

核心功能:
- 安全的凭据存储和加密
- 配置验证和完整性检查
- 动态配置加载和热更新
- 多租户配置隔离
- 配置备份和恢复
"""

from typing import Optional
from datetime import datetime
from pathlib import Path

from .provider_config import (
    GlobalProviderConfig,
    TenantProviderConfig,
    ProviderConfig,
    ProviderType
)
from .config_manager_modules.encryption import ConfigEncryption
from .config_manager_modules.validator import ConfigValidator
from .config_manager_modules.loader import ConfigLoader
from .config_manager_modules.serializer import ConfigSerializer
from .config_manager_modules.backup_manager import BackupManager
from src.utils import get_component_logger, ErrorHandler


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigEncryptionError(Exception):
    """配置加密错误"""
    pass


class ConfigManager:
    """
    配置管理器主类
    
    提供安全的配置存储、加载和管理功能。
    支持配置加密和多租户隔离。
    """
    
    def __init__(self, config_dir: str = "config", encryption_key: Optional[str] = None):
        """
        初始化配置管理器
        
        参数:
            config_dir: 配置文件目录
            encryption_key: 加密密钥，None时从环境变量获取
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.logger = get_component_logger(__name__, "ConfigManager")
        self.error_handler = ErrorHandler("config_manager")
        
        # 初始化子组件
        self.encryption = ConfigEncryption(encryption_key)
        self.validator = ConfigValidator()
        self.loader = ConfigLoader(self.config_dir, self.encryption)
        self.serializer = ConfigSerializer(self.encryption)
        self.backup_manager = BackupManager(self.config_dir)
        
        # 配置缓存
        self._config_cache: Optional[GlobalProviderConfig] = None
        self._config_last_modified: Optional[datetime] = None
        
        self.logger.info("配置管理器初始化完成")
    
    async def load_global_config(self, force_reload: bool = False) -> GlobalProviderConfig:
        """
        加载全局配置
        
        参数:
            force_reload: 是否强制重新加载
            
        返回:
            GlobalProviderConfig: 全局配置对象
        """
        try:
            # 检查缓存
            if not force_reload and self._config_cache:
                if self.loader.config_file_exists("global_config.json"):
                    file_modified = self.loader.get_file_modified_time("global_config.json")
                    if self._config_last_modified and file_modified <= self._config_last_modified:
                        return self._config_cache
            
            # 使用加载器加载配置
            global_config = await self.loader.load_global_config()
            
            # 更新缓存
            self._config_cache = global_config
            self._config_last_modified = datetime.now()
            
            self.logger.info("全局配置加载成功")
            return global_config
            
        except Exception as e:
            self.error_handler.handle_error(e, {"operation": "load_global_config"})
            raise
    
    async def save_global_config(self, config: GlobalProviderConfig):
        """
        保存全局配置
        
        参数:
            config: 全局配置对象
        """
        try:
            # 使用加载器保存配置
            await self.loader.save_global_config(config)
            
            # 更新缓存
            self._config_cache = config
            self._config_last_modified = datetime.now()
            
            self.logger.info("全局配置保存成功")
            
        except Exception as e:
            self.error_handler.handle_error(e, {"operation": "save_global_config"})
            raise
    
    async def load_tenant_config(self, tenant_id: str) -> Optional[TenantProviderConfig]:
        """
        加载租户配置
        
        参数:
            tenant_id: 租户ID
            
        返回:
            TenantProviderConfig: 租户配置对象或None
        """
        try:
            return await self.loader.load_tenant_config(tenant_id)
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "operation": "load_tenant_config",
                "tenant_id": tenant_id
            })
            return None
    
    async def save_tenant_config(self, tenant_config: TenantProviderConfig):
        """
        保存租户配置
        
        参数:
            tenant_config: 租户配置对象
        """
        try:
            await self.loader.save_tenant_config(tenant_config)
            
            # 更新全局配置缓存
            if self._config_cache:
                self._config_cache.tenant_configs[tenant_config.tenant_id] = tenant_config
            
            self.logger.info(f"租户配置保存成功: {tenant_config.tenant_id}")
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "operation": "save_tenant_config",
                "tenant_id": tenant_config.tenant_id
            })
            raise
    
    async def create_provider_config(
        self,
        provider_type: ProviderType,
        api_key: str,
        api_base: Optional[str] = None,
        organization: Optional[str] = None,
        **kwargs
    ) -> ProviderConfig:
        """
        创建供应商配置
        
        参数:
            provider_type: 供应商类型
            api_key: API密钥
            api_base: API基础URL
            organization: 组织ID
            **kwargs: 其他配置参数
            
        返回:
            ProviderConfig: 供应商配置对象
        """
        try:
            # 使用工厂方法创建配置
            provider_config = self._create_provider_config_factory(
                provider_type, api_key, api_base, organization, **kwargs
            )
            
            # 验证配置
            await self.validate_provider_config(provider_config)
            
            self.logger.info(f"供应商配置创建成功: {provider_type}")
            return provider_config
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "operation": "create_provider_config",
                "provider_type": provider_type
            })
            raise
    
    async def validate_provider_config(self, config: ProviderConfig) -> bool:
        """
        验证供应商配置
        
        参数:
            config: 供应商配置对象
            
        返回:
            bool: 验证是否通过
            
        异常:
            ConfigValidationError: 验证失败时抛出
        """
        return await self.validator.validate_provider_config(config, self.encryption)
    
    def _create_provider_config_factory(
        self,
        provider_type: ProviderType,
        api_key: str,
        api_base: Optional[str] = None,
        organization: Optional[str] = None,
        **kwargs
    ) -> ProviderConfig:
        """创建供应商配置的工厂方法"""
        from .provider_config import ProviderCredentials, ModelConfig
        
        # 创建加密的凭据
        encrypted_api_key = self.encryption.encrypt_sensitive_data(api_key)
        credentials = ProviderCredentials(
            api_key=encrypted_api_key,
            api_base=api_base,
            organization=organization
        )
        
        # 创建默认模型配置
        models = self._get_default_models_for_provider(provider_type)
        
        return ProviderConfig(
            provider_type=provider_type,
            credentials=credentials,
            models=models,
            is_enabled=kwargs.get('is_enabled', True),
            priority=kwargs.get('priority', 1),
            rate_limit_rpm=kwargs.get('rate_limit_rpm', 1000),
            rate_limit_tpm=kwargs.get('rate_limit_tpm', 100000),
            timeout_seconds=kwargs.get('timeout_seconds', 30),
            retry_attempts=kwargs.get('retry_attempts', 3)
        )
    
    def _get_default_models_for_provider(self, provider_type: ProviderType) -> dict:
        """获取供应商的默认模型配置"""
        from .provider_config import ModelConfig
        
        defaults = {
            ProviderType.OPENAI: {
                "gpt-4": ModelConfig(model_name="gpt-4", max_tokens=8192, temperature=0.7),
                "gpt-3.5-turbo": ModelConfig(model_name="gpt-3.5-turbo", max_tokens=4096, temperature=0.7)
            },
            ProviderType.ANTHROPIC: {
                "claude-3-sonnet": ModelConfig(model_name="claude-3-sonnet-20240229", max_tokens=4096, temperature=0.7)
            },
            ProviderType.GEMINI: {
                "gemini-pro": ModelConfig(model_name="gemini-pro", max_tokens=2048, temperature=0.7)
            },
            ProviderType.DEEPSEEK: {
                "deepseek-chat": ModelConfig(model_name="deepseek-chat", max_tokens=4096, temperature=0.7)
            }
        }
        
        return defaults.get(provider_type, {})
    
    async def backup_config(self, backup_dir: Optional[str] = None) -> str:
        """
        备份配置
        
        参数:
            backup_dir: 备份目录，None时使用默认目录
            
        返回:
            str: 备份文件路径
        """
        try:
            # 加载当前配置
            global_config = await self.load_global_config()
            
            # 使用备份管理器进行备份
            backup_file = await self.backup_manager.backup_config(
                global_config, self.serializer, backup_dir
            )
            
            self.logger.info(f"配置备份完成: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.error_handler.handle_error(e, {"operation": "backup_config"})
            raise
    
    async def restore_config(self, backup_file: str):
        """
        恢复配置
        
        参数:
            backup_file: 备份文件路径
        """
        try:
            # 使用备份管理器恢复配置
            global_config = await self.backup_manager.restore_config(
                backup_file, self.serializer
            )
            
            # 保存恢复的配置
            await self.save_global_config(global_config)
            
            self.logger.info(f"配置恢复完成: {backup_file}")
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "operation": "restore_config",
                "backup_file": backup_file
            })
            raise
    
    def list_backups(self) -> list:
        """列出所有备份文件"""
        return self.backup_manager.list_backups()
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        return self.backup_manager.cleanup_old_backups(keep_count)
    
    def get_config_stats(self) -> dict:
        """获取配置统计信息"""
        stats = {
            "cache_enabled": self._config_cache is not None,
            "last_modified": self._config_last_modified.isoformat() if self._config_last_modified else None,
            "encryption_enabled": self.encryption.is_encryption_enabled(),
            "config_dir": str(self.config_dir)
        }
        
        if self._config_cache:
            stats.update({
                "default_providers_count": len(self._config_cache.default_providers),
                "tenant_configs_count": len(self._config_cache.tenant_configs)
            })
        
        return stats