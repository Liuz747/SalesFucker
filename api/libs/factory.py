"""
基础设施客户端工厂

提供基于类的接口来构建和缓存基础设施客户端（数据库、Redis、Elasticsearch、Milvus），并复用既有的客户端构造逻辑。
"""

from contextlib import asynccontextmanager
from typing import Optional

from elasticsearch import AsyncElasticsearch
from pymilvus import MilvusClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client

from infra.db import (
    create_db_engine,
    create_session_factory,
    test_db_connection,
    close_engine
)
from infra.cache import (
    create_redis_client,
    test_redis_connection,
    close_redis_client
)
from infra.ops import (
    get_es_client,
    close_es_client,
    verify_es_connection,
    create_memory_index,
    get_milvus_connection,
    close_milvus_connection,
    verify_milvus_connection,
    get_temporal_client,
    verify_temporal_connection
)
from libs.types import InfraClients
from utils import get_component_logger

logger = get_component_logger(__name__)


class InfraFactory:
    """
    延迟初始化基础设施客户端的工厂。

    实例会缓存已创建的客户端，避免重复构建，同时保持生命周期管理的显式性。
    """

    def __init__(self):
        self._clients: Optional[InfraClients] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def create_clients(self) -> InfraClients:
        """
        如未创建则初始化基础设施客户端。

        Returns:
            InfraClients: 已缓存或新创建的客户端集合。
        """
        if self._clients is not None:
            return self._clients

        logger.info("开始初始化基础设施客户端")

        # Database engine
        db_engine = await create_db_engine()
        self._session_factory = create_session_factory(db_engine)
        logger.info("PostgreSQL 数据库引擎准备完成")

        # Redis client
        redis = await create_redis_client()
        logger.info("Redis 客户端准备完成")

        # Elasticsearch client
        elasticsearch: Optional[AsyncElasticsearch] = None
        try:
            elasticsearch = await get_es_client()
            logger.info("Elasticsearch 客户端准备完成")
        except Exception as e:
            logger.warning(f"Elasticsearch 连接初始化失败: {e}")

        # Milvus client
        milvus: Optional[MilvusClient] = None
        try:
            milvus = await get_milvus_connection()
            logger.info("Milvus 连接准备完成")
        except ConnectionError as e:
            logger.warning(f"Milvus 连接初始化失败: {e}")

        # Temporal client
        temporal: Optional[Client] = None
        try:
            temporal = await get_temporal_client()
            logger.info("Temporal 连接准备完成")
        except ConnectionError as e:
            logger.warning(f"Temporal 连接初始化失败:{e}")

        self._clients = InfraClients(
            db_engine=db_engine,
            redis=redis,
            elasticsearch=elasticsearch,
            milvus=milvus,
            temporal=temporal
        )

        logger.info("基础设施客户端初始化完成")
        return self._clients

    def get_cached_clients(self) -> InfraClients:
        """
        返回已缓存的客户端，不触发初始化。

        Returns:
            InfraClients: 创建的客户端集合。
        """
        if self._clients is None:
            raise RuntimeError("InfraFactory未初始化，请先调用create_clients()")
        return self._clients

    @asynccontextmanager
    async def get_db_session(self):
        """
        便捷方法：获取数据库会话

        用法:
            async with infra_registry.get_db_session() as session:
                # 数据库操作
                pass
        """
        if self._session_factory is None:
            raise RuntimeError("InfraFactory未初始化，请先调用create_clients()")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库操作失败，本次操作已取消: {e}")
            raise
        finally:
            await session.close()

    async def test_clients(self):
        """测试所有已初始化的基础设施客户端,各服务连接状态记录在日志中。"""
        if self._clients is None:
            logger.warning("客户端未初始化，无法测试")
            return

        logger.info("开始测试基础设施客户端连接")

        # Test database connection
        try:
            db_flag = await test_db_connection(self._clients.db_engine)
            if db_flag:
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
                await create_memory_index(self._clients.elasticsearch)
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

        await close_redis_client(self._clients.redis)
        await close_engine(self._clients.db_engine)

        self._clients = None
        self._session_factory = None
        logger.info("基础设施客户端关闭完成")


# 全局注册表实例
infra_registry = InfraFactory()

__all__ = ["infra_registry"]
