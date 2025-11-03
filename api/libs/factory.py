"""
基础设施客户端工厂

提供基于类的接口来构建和缓存基础设施客户端（数据库、Redis、Elasticsearch、Milvus），并复用既有的客户端构造逻辑。
"""

from typing import Optional

from elasticsearch import AsyncElasticsearch
from pymilvus import MilvusClient
from temporalio.client import Client

from infra.db import get_engine, close_db_connections, test_db_connection
from infra.cache import get_redis_client, close_redis_client, test_redis_connection
from infra.ops import (
    get_es_client,
    close_es_client,
    verify_es_connection,
    get_milvus_connection,
    close_milvus_connection,
    verify_milvus_connection,
    get_temporal_client,
    verify_temporal_connection
)
from utils import get_component_logger
from .types import InfraClients

logger = get_component_logger(__name__)


class InfraFactory:
    """
    延迟初始化基础设施客户端的工厂。

    实例会缓存已创建的客户端，避免重复构建，同时保持生命周期管理的显式性。
    """

    def __init__(self):
        self._clients: Optional[InfraClients] = None

    async def create_clients(self) -> InfraClients:
        """
        如未创建则初始化基础设施客户端。

        Returns:
            InfraClients: 已缓存或新创建的客户端集合。
        """
        if self._clients is not None:
            return self._clients

        logger.info("开始初始化基础设施客户端")

        # Database engine (async)
        db_engine = await get_engine()
        logger.info("PostgreSQL 数据库引擎准备完成")

        # Redis client
        redis = await get_redis_client()
        logger.info("Redis 客户端准备完成")

        # Elasticsearch client (optional)
        elasticsearch: Optional[AsyncElasticsearch] = None
        try:
            elasticsearch = await get_es_client()
            logger.info("Elasticsearch 客户端准备完成")
        except Exception as exc:
            logger.warning("Elasticsearch 连接初始化失败: %s", exc, exc_info=True)

        # Milvus is optional
        milvus: Optional[MilvusClient] = None
        try:
            milvus = await get_milvus_connection()
            logger.info("Milvus 连接准备完成")
        except Exception as exc:
            logger.warning("Milvus 连接初始化失败: %s", exc, exc_info=True)

        temporal: Optional[Client] = None
        try:
            temporal = await get_temporal_client()
            logger.info("Temporal 连接准备完成")
        except Exception as exc:
            logger.warning("Temporal 连接初始化失败: %s", exc, exc_info=True)

        self._clients = InfraClients(
            db_engine=db_engine,
            redis=redis,
            elasticsearch=elasticsearch,
            milvus=milvus,
            temporal=temporal
        )

        logger.info("基础设施客户端初始化完成")
        return self._clients

    def get_cached_clients(self) -> Optional[InfraClients]:
        """
        返回已缓存的客户端，不触发初始化。

        Returns:
            Optional[InfraClients]: 之前创建的客户端集合。
        """
        return self._clients

    async def test_clients(self):
        """测试所有已初始化的基础设施客户端,各服务连接状态记录在日志中。"""
        if self._clients is None:
            logger.warning("客户端未初始化，无法测试")
            return

        logger.info("开始测试基础设施客户端连接")

        # Test database connection
        try:
            db_ok = await test_db_connection()
            if db_ok:
                logger.info("✓ 数据库连接成功")
            else:
                logger.warning("✗ 数据库连接失败")
        except Exception as exc:
            logger.warning("✗ 数据库连接测试异常: %s", exc, exc_info=True)

        # Test Redis connection
        if await test_redis_connection(self._clients.redis):
            logger.info("✓ Redis连接成功")
        else:
            logger.warning("✗ Redis连接失败")

        # Test Elasticsearch connection (optional)
        if self._clients.elasticsearch:
            if await verify_es_connection(self._clients.elasticsearch):
                logger.info("✓ Elasticsearch连接测试成功")
            else:
                logger.warning("✗ Elasticsearch连接测试失败")
        else:
            logger.info("○ Elasticsearch未配置")

        # Test Milvus connection (optional)
        if self._clients.milvus:
            await verify_milvus_connection(self._clients.milvus)
        else:
            logger.info("○ Milvus未配置")

        if self._clients.temporal:
            if await verify_temporal_connection(self._clients.temporal):
                logger.info("✓ Temporal连接测试成功")
            else:
                logger.warning("✗ Temporal连接测试失败")
        else:
            logger.info("○ Temporal未配置")

        logger.info("基础设施客户端连接测试完成")


    async def shutdown_clients(self):
        """关闭所有已初始化的基础设施客户端。"""
        if self._clients is None:
            return

        logger.info("开始关闭基础设施客户端")

        if self._clients.milvus:
            await close_milvus_connection(self._clients.milvus)

        if self._clients.elasticsearch:
            await close_es_client(self._clients.elasticsearch)

        await close_redis_client()
        await close_db_connections()

        self._clients = None
        logger.info("基础设施客户端关闭完成")


# 全局注册表实例
infra_registry = InfraFactory()