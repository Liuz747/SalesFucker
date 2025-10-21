"""
基础设施生命周期编排工具

集中管理共享基础设施客户端的初始化与关闭，方便 FastAPI 生命周期钩子统一调用。
"""
from typing import Optional

from utils import get_component_logger
from infra.factory import InfrastructureFactory, InfrastructureClients

logger = get_component_logger(__name__)

_factory: InfrastructureFactory = InfrastructureFactory()
_cached_clients: Optional[InfrastructureClients] = None


async def initialize_infra_clients() -> InfrastructureClients:
    """
    初始化基础设施客户端并缓存结果，供后续复用。

    Returns:
        InfrastructureClients: 已初始化的客户端集合。
    """
    global _cached_clients

    if _cached_clients is None:
        _cached_clients = await _factory.create_clients()

    return _cached_clients


async def shutdown_infra_clients() -> None:
    """关闭已初始化的基础设施客户端。"""
    global _cached_clients

    await _factory.shutdown_clients()
    _cached_clients = None
