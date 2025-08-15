"""
简化配置管理器模块

该模块提供简单的LLM供应商配置加载和管理功能。
遵循现代最佳实践：环境变量存储API密钥，JSON文件存储配置。

核心功能:
- 从环境变量加载API密钥
- JSON配置文件加载和保存
- 基本配置验证
- 多租户配置支持
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

from .provider_config import (
    GlobalProviderConfig,
    TenantProviderConfig,
    ProviderConfig,
    ProviderType,
    ProviderCredentials,
    ModelConfig
)
from utils import get_component_logger


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigManager:
    """
    简化配置管理器
    
    提供简单的配置加载和保存功能，遵循现代最佳实践。
    API密钥通过环境变量管理，配置通过JSON文件管理。
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器
        
        参数:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.logger = get_component_logger(__name__, "ConfigManager")
        
        # 配置缓存
        self._global_config: Optional[GlobalProviderConfig] = None
        
        self.logger.info("简化配置管理器初始化完成")
    
    async def load_global_config(self) -> GlobalProviderConfig:
        """
        加载全局配置
        
        返回:
            GlobalProviderConfig: 全局配置对象
        """
        try:
            # 检查缓存
            if self._global_config:
                return self._global_config
            
            config_file = self.config_dir / "global_config.json"
            
            if config_file.exists():
                # 从文件加载配置
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 解析配置
                global_config = self._parse_global_config(config_data)
            else:
                # 创建默认配置
                global_config = self._create_default_config()
                # 保存默认配置
                await self.save_global_config(global_config)
            
            # 从环境变量加载API密钥
            self._load_api_keys_from_env(global_config)
            
            # 缓存配置
            self._global_config = global_config
            
            self.logger.info("全局配置加载成功")
            return global_config
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {str(e)}")
            raise ConfigValidationError(f"配置加载失败: {str(e)}")
    
    async def save_global_config(self, config: GlobalProviderConfig):
        """
        保存全局配置
        
        参数:
            config: 全局配置对象
        """
        try:
            config_file = self.config_dir / "global_config.json"
            
            # 序列化配置（不包含API密钥）
            config_data = self._serialize_global_config(config)
            
            # 保存到文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # 更新缓存
            self._global_config = config
            
            self.logger.info("全局配置保存成功")
            
        except Exception as e:
            self.logger.error(f"配置保存失败: {str(e)}")
            raise ConfigValidationError(f"配置保存失败: {str(e)}")
    
    def _load_api_keys_from_env(self, config: GlobalProviderConfig):
        """从环境变量加载API密钥"""
        env_mapping = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY", 
            ProviderType.GEMINI: "GEMINI_API_KEY",
            ProviderType.DEEPSEEK: "DEEPSEEK_API_KEY"
        }
        
        for provider_type, provider_config in config.default_providers.items():
            env_var = env_mapping.get(provider_type)
            if env_var:
                api_key = os.getenv(env_var)
                if api_key:
                    provider_config.credentials.api_key = api_key
                    self.logger.debug(f"从环境变量加载API密钥: {provider_type}")
                else:
                    self.logger.warning(f"环境变量 {env_var} 未设置")
    
    def _create_default_config(self) -> GlobalProviderConfig:
        """创建默认配置"""
        default_providers = {}
        
        # OpenAI配置
        if os.getenv("OPENAI_API_KEY"):
            default_providers[ProviderType.OPENAI] = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                credentials=ProviderCredentials(api_key=""),  # 将从环境变量加载
                models={
                    "gpt-4": ModelConfig(model_name="gpt-4", max_tokens=8192, temperature=0.7),
                    "gpt-3.5-turbo": ModelConfig(model_name="gpt-3.5-turbo", max_tokens=4096, temperature=0.7)
                },
                is_enabled=True,
                priority=1
            )
        
        # Anthropic配置
        if os.getenv("ANTHROPIC_API_KEY"):
            default_providers[ProviderType.ANTHROPIC] = ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                credentials=ProviderCredentials(api_key=""),
                models={
                    "claude-3-sonnet": ModelConfig(model_name="claude-3-sonnet-20240229", max_tokens=4096, temperature=0.7)
                },
                is_enabled=True,
                priority=2
            )
        
        # Gemini配置
        if os.getenv("GEMINI_API_KEY"):
            default_providers[ProviderType.GEMINI] = ProviderConfig(
                provider_type=ProviderType.GEMINI,
                credentials=ProviderCredentials(api_key=""),
                models={
                    "gemini-pro": ModelConfig(model_name="gemini-pro", max_tokens=2048, temperature=0.7)
                },
                is_enabled=True,
                priority=3
            )
        
        # DeepSeek配置
        if os.getenv("DEEPSEEK_API_KEY"):
            default_providers[ProviderType.DEEPSEEK] = ProviderConfig(
                provider_type=ProviderType.DEEPSEEK,
                credentials=ProviderCredentials(api_key=""),
                models={
                    "deepseek-chat": ModelConfig(model_name="deepseek-chat", max_tokens=4096, temperature=0.7)
                },
                is_enabled=True,
                priority=4
            )
        
        return GlobalProviderConfig(
            default_providers=default_providers,
            tenant_configs={}
        )
    
    def _parse_global_config(self, config_data: Dict[str, Any]) -> GlobalProviderConfig:
        """解析全局配置数据"""
        default_providers = {}
        
        for provider_type_str, provider_data in config_data.get("default_providers", {}).items():
            provider_type = ProviderType(provider_type_str)
            
            # 解析模型配置
            models = {}
            for model_name, model_data in provider_data.get("models", {}).items():
                models[model_name] = ModelConfig(
                    model_name=model_data["model_name"],
                    max_tokens=model_data.get("max_tokens", 2048),
                    temperature=model_data.get("temperature", 0.7)
                )
            
            # 创建供应商配置
            provider_config = ProviderConfig(
                provider_type=provider_type,
                credentials=ProviderCredentials(api_key=""),  # 将从环境变量加载
                models=models,
                is_enabled=provider_data.get("is_enabled", True),
                priority=provider_data.get("priority", 1),
                rate_limit_rpm=provider_data.get("rate_limit_rpm", 1000),
                rate_limit_tpm=provider_data.get("rate_limit_tpm", 100000)
            )
            
            default_providers[provider_type] = provider_config
        
        return GlobalProviderConfig(
            default_providers=default_providers,
            tenant_configs={}
        )
    
    def _serialize_global_config(self, config: GlobalProviderConfig) -> Dict[str, Any]:
        """序列化全局配置（不包含API密钥）"""
        default_providers = {}
        
        for provider_type, provider_config in config.default_providers.items():
            models = {}
            for model_name, model_config in provider_config.models.items():
                models[model_name] = {
                    "model_name": model_config.model_name,
                    "max_tokens": model_config.max_tokens,
                    "temperature": model_config.temperature
                }
            
            default_providers[provider_type.value] = {
                "models": models,
                "is_enabled": provider_config.is_enabled,
                "priority": provider_config.priority,
                "rate_limit_rpm": provider_config.rate_limit_rpm,
                "rate_limit_tpm": provider_config.rate_limit_tpm
            }
        
        return {
            "default_providers": default_providers,
            "tenant_configs": {}  # 简化版暂不支持租户配置
        }
    
    async def validate_config(self, config: GlobalProviderConfig) -> bool:
        """
        验证配置
        
        参数:
            config: 配置对象
            
        返回:
            bool: 验证是否通过
        """
        try:
            # 基本验证
            if not config.default_providers:
                raise ConfigValidationError("必须配置至少一个供应商")
            
            # 验证每个供应商
            for provider_type, provider_config in config.default_providers.items():
                if not provider_config.credentials.api_key:
                    self.logger.warning(f"供应商 {provider_type} 缺少API密钥")
                
                if not provider_config.models:
                    raise ConfigValidationError(f"供应商 {provider_type} 必须配置至少一个模型")
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"配置验证失败: {str(e)}")