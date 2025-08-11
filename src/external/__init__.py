"""
外部API客户端模块

该模块提供与外部服务的集成客户端，包括后端API、第三方服务等。
主要用于查询外部数据，不包含业务逻辑处理。

核心组件:
- BaseClient: 基础HTTP客户端
- DeviceClient: 设备查询客户端
- Config: 外部API配置
"""

from .base_client import BaseClient, ExternalAPIError
from .config import ExternalConfig
from .clients.device_client import DeviceClient

__all__ = [
    "BaseClient",
    "ExternalAPIError", 
    "ExternalConfig",
    "DeviceClient"
]