"""
基础设施客户端工厂抽象

提供基于类的接口来构建和缓存基础设施客户端（数据库、Redis、Elasticsearch、Milvus），并复用既有的客户端构造逻辑。
"""
from dataclasses import dataclass
from typing import Optional

from utils import get_component_logger
from infra.db import get_engine, close_db_connections
from infra.cache import get_redis_client, close_redis_client
from infra.ops import (
    get_es_client,
    close_es_client,
    get_milvus_connection,
    close_milvus_connection,
)

logger = get_component_logger(__name__)


@dataclass
class InfrastructureClients:
    """已初始化基础设施客户端的容器。"""

    db_engine: object
    redis: object
    elasticsearch: object
    milvus_alias: Optional[str]


class InfrastructureFactory:
    """
    延迟初始化基础设施客户端的工厂。

    实例会缓存已创建的客户端，避免重复构建，同时保持生命周期管理的显式性。
    """

    def __init__(self) -> None:
        self._clients: Optional[InfrastructureClients] = None

    async def create_clients(self) -> InfrastructureClients:
        """
        如未创建则初始化基础设施客户端。

        Returns:
            InfrastructureClients: 已缓存或新创建的客户端集合。
        """
        if self._clients is not None:
            return self._clients

        logger.info("开始初始化基础设施客户端")

        # Database engine (async)
        db_engine = await get_engine()
        logger.info("数据库引擎准备完成")

        # Redis client
        redis = await get_redis_client()
        logger.info("Redis客户端准备完成")

        # Elasticsearch client
        elasticsearch = await get_es_client()
        logger.info("Elasticsearch客户端准备完成")

        # Milvus is optional
        milvus_alias: Optional[str] = None
        try:
            await get_milvus_connection()
            milvus_alias = "default"
            logger.info("Milvus连接准备完成")
        except Exception as exc:
            logger.warning("Milvus连接初始化失败: %s", exc, exc_info=True)

        self._clients = InfrastructureClients(
            db_engine=db_engine,
            redis=redis,
            elasticsearch=elasticsearch,
            milvus_alias=milvus_alias,
        )

        logger.info("基础设施客户端初始化完成")
        return self._clients

    def get_cached_clients(self) -> Optional[InfrastructureClients]:
        """
        返回已缓存的客户端，不触发初始化。

        Returns:
            Optional[InfrastructureClients]: 之前创建的客户端集合。
        """
        return self._clients

    async def shutdown_clients(self) -> None:
        """关闭所有已初始化的基础设施客户端。"""
        if self._clients is None:
            return

        logger.info("开始关闭基础设施客户端")

        try:
            await close_milvus_connection()
        except Exception as exc:
            logger.warning("Milvus连接关闭失败: %s", exc, exc_info=True)

        await close_es_client()
        await close_redis_client()
        await close_db_connections()

        self._clients = None
        logger.info("基础设施客户端关闭完成")
