"""
应用程序集成配置模块

提供集成所有配置模块的主配置类。
"""

from pydantic_settings import SettingsConfigDict

from .deploy import DeploymentConfig
from .module import ModuleConfig
from .service import ServiceConfig
from .storage import StorageConfig


class AppConfig(DeploymentConfig, StorageConfig, ServiceConfig, ModuleConfig):
    """
    集成配置类

    继承所有配置模块，提供统一的配置接口。
    保持向后兼容性的同时提供模块化配置结构。

    包含的配置模块：
    - DeploymentConfig: 部署配置（应用信息、API、日志、性能）
    - StorageConfig: 存储系统配置（Elasticsearch、Redis、PostgreSQL、Milvus）
    - ServiceConfig: 服务配置（LLM提供商、身份验证、外部服务）
    - ModuleConfig: 模块配置（意向阈值）
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )