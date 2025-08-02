"""
配置序列化器模块

负责配置对象的序列化和反序列化。
"""

from typing import Dict, Any
from datetime import datetime

from ..provider_config import (
    GlobalProviderConfig, 
    TenantProviderConfig, 
    ProviderConfig,
    ProviderCredentials,
    ModelConfig,
    AgentProviderMapping,
    RoutingRule,
    CostConfig,
    ProviderType
)
from .encryption import ConfigEncryption


class ConfigSerializer:
    """配置序列化器类"""
    
    def __init__(self, encryption: ConfigEncryption):
        """
        初始化序列化器
        
        参数:
            encryption: 加密管理器
        """
        self.encryption = encryption
    
    def parse_global_config(self, config_data: Dict[str, Any]) -> GlobalProviderConfig:
        """解析全局配置数据"""
        # 解析默认供应商配置
        default_providers = {}
        for provider_type, provider_data in config_data.get("default_providers", {}).items():
            provider_config = self.parse_provider_config(provider_data)
            default_providers[provider_type] = provider_config
        
        # 创建全局配置对象
        global_config = GlobalProviderConfig(
            default_providers=default_providers,
            tenant_configs={},  # 租户配置单独加载
            global_settings=config_data.get("global_settings", {})
        )
        
        return global_config
    
    def parse_tenant_config(self, config_data: Dict[str, Any]) -> TenantProviderConfig:
        """解析租户配置数据"""
        # 解析供应商配置
        provider_configs = {}
        for provider_type, provider_data in config_data.get("provider_configs", {}).items():
            provider_config = self.parse_provider_config(provider_data)
            provider_configs[provider_type] = provider_config
        
        # 解析智能体映射
        agent_mappings = {}
        for agent_type, mapping_data in config_data.get("agent_mappings", {}).items():
            agent_mapping = AgentProviderMapping(**mapping_data)
            agent_mappings[agent_type] = agent_mapping
        
        # 解析路由规则
        routing_rules = []
        for rule_data in config_data.get("routing_rules", []):
            routing_rule = RoutingRule(**rule_data)
            routing_rules.append(routing_rule)
        
        # 解析成本配置
        cost_config_data = config_data.get("cost_config", {})
        cost_config = CostConfig(**cost_config_data) if cost_config_data else CostConfig()
        
        # 创建租户配置对象
        tenant_config = TenantProviderConfig(
            tenant_id=config_data["tenant_id"],
            provider_configs=provider_configs,
            agent_mappings=agent_mappings,
            routing_rules=routing_rules,
            cost_config=cost_config,
            created_at=datetime.fromisoformat(config_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(config_data.get("updated_at", datetime.now().isoformat()))
        )
        
        return tenant_config
    
    def parse_provider_config(self, provider_data: Dict[str, Any]) -> ProviderConfig:
        """解析供应商配置数据"""
        # 解析凭据
        credentials_data = provider_data["credentials"]
        credentials = ProviderCredentials(**credentials_data)
        
        # 解析模型配置
        models = {}
        for model_name, model_data in provider_data.get("models", {}).items():
            model_config = ModelConfig(**model_data)
            models[model_name] = model_config
        
        # 创建供应商配置对象
        provider_config = ProviderConfig(
            provider_type=ProviderType(provider_data["provider_type"]),
            credentials=credentials,
            models=models,
            is_enabled=provider_data.get("is_enabled", True),
            priority=provider_data.get("priority", 1),
            rate_limit_rpm=provider_data.get("rate_limit_rpm", 1000),
            rate_limit_tpm=provider_data.get("rate_limit_tpm", 100000),
            timeout_seconds=provider_data.get("timeout_seconds", 30),
            retry_attempts=provider_data.get("retry_attempts", 3)
        )
        
        return provider_config
    
    def serialize_global_config(self, config: GlobalProviderConfig) -> Dict[str, Any]:
        """序列化全局配置"""
        config_data = {
            "default_providers": {},
            "global_settings": config.global_settings
        }
        
        # 序列化默认供应商配置
        for provider_type, provider_config in config.default_providers.items():
            config_data["default_providers"][provider_type] = self.serialize_provider_config(provider_config)
        
        return config_data
    
    def serialize_tenant_config(self, config: TenantProviderConfig) -> Dict[str, Any]:
        """序列化租户配置"""
        config_data = {
            "tenant_id": config.tenant_id,
            "provider_configs": {},
            "agent_mappings": {},
            "routing_rules": [],
            "cost_config": config.cost_config.dict(),
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat()
        }
        
        # 序列化供应商配置
        for provider_type, provider_config in config.provider_configs.items():
            config_data["provider_configs"][provider_type] = self.serialize_provider_config(provider_config)
        
        # 序列化智能体映射
        for agent_type, agent_mapping in config.agent_mappings.items():
            config_data["agent_mappings"][agent_type] = agent_mapping.dict()
        
        # 序列化路由规则
        for routing_rule in config.routing_rules:
            config_data["routing_rules"].append(routing_rule.dict())
        
        return config_data
    
    def serialize_provider_config(self, config: ProviderConfig) -> Dict[str, Any]:
        """序列化供应商配置"""
        config_data = {
            "provider_type": config.provider_type.value,
            "credentials": config.credentials.dict(),
            "models": {},
            "is_enabled": config.is_enabled,
            "priority": config.priority,
            "rate_limit_rpm": config.rate_limit_rpm,
            "rate_limit_tpm": config.rate_limit_tpm,
            "timeout_seconds": config.timeout_seconds,
            "retry_attempts": config.retry_attempts
        }
        
        # 序列化模型配置
        for model_name, model_config in config.models.items():
            config_data["models"][model_name] = model_config.dict()
        
        return config_data