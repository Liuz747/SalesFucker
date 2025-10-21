"""
基础设施客户端注册表

集中管理数据库、缓存、搜索和向量存储的客户端实例，
提供统一的初始化、获取与关闭流程。
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from elasticsearch import AsyncElasticsearch
from pymilvus import MilvusException, connections
from redis.asyncio import ConnectionPool, Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)


class InfraRegistry:
    """
    基础设施客户端注册表

    负责懒加载各类外部服务客户端，并提供统一的生命周期管理。
    """

    def __init__(self):
        # Postgres
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._db_lock = asyncio.Lock()

        # Redis
        self._redis_pool: Optional[ConnectionPool] = None
        self._redis_lock = asyncio.Lock()

        # Elasticsearch
        self._es_client: Optional[AsyncElasticsearch] = None
        self._es_lock = asyncio.Lock()

        # Milvus
        self._milvus_connected = False
        self._milvus_lock = asyncio.Lock()

    # --- Database helpers -------------------------------------------------
    async def get_db_engine(self) -> AsyncEngine:
        """获取或初始化数据库引擎。"""
        if self._engine is None:
            async with self._db_lock:
                if self._engine is None:
                    logger.info(f"初始化PostgreSQL连接: {mas_config.DB_HOST}")
                    self._engine = create_async_engine(
                        mas_config.postgres_url,
                        pool_size=mas_config.SQLALCHEMY_POOL_SIZE,
                        max_overflow=mas_config.SQLALCHEMY_MAX_OVERFLOW,
                        pool_pre_ping=mas_config.SQLALCHEMY_POOL_PRE_PING,
                        pool_recycle=mas_config.SQLALCHEMY_POOL_RECYCLE,
                        connect_args={
                            "command_timeout": mas_config.SQLALCHEMY_COMMAND_TIMEOUT,
                            "server_settings": {
                                "application_name": mas_config.APP_NAME,
                            },
                        },
                        echo=mas_config.SQLALCHEMY_ECHO,
                    )
                    logger.info("PostgreSQL引擎初始化完成")
        return self._engine  # type: ignore[return-value]

    async def get_db_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """获取或初始化Session工厂。"""
        if self._session_factory is None:
            async with self._db_lock:
                if self._session_factory is None:
                    engine = await self.get_db_engine()
                    self._session_factory = async_sessionmaker(
                        engine,
                        class_=AsyncSession,
                        expire_on_commit=False,
                        autoflush=True,
                        autocommit=False,
                    )
        return self._session_factory  # type: ignore[return-value]

    async def close_db(self) -> None:
        """关闭数据库资源。"""
        async with self._db_lock:
            if self._engine:
                await self._engine.dispose()
                self._engine = None
                self._session_factory = None
                logger.info("数据库连接已关闭")

    async def verify_db_connection(self) -> bool:
        """测试数据库连通性。"""
        try:
            engine = await self.get_db_engine()
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
            logger.info("数据库连接测试成功")
            return row is not None and row[0] == 1
        except Exception as exc:  # noqa: BLE001
            logger.error(f"数据库连接测试失败: {exc}")
            return False

    # --- Redis helpers ----------------------------------------------------
    async def get_redis_pool(self) -> ConnectionPool:
        """获取或初始化Redis连接池。"""
        if self._redis_pool is None:
            async with self._redis_lock:
                if self._redis_pool is None:
                    logger.info(f"初始化Redis连接: {mas_config.REDIS_HOST}")
                    self._redis_pool = ConnectionPool.from_url(
                        mas_config.redis_url,
                        decode_responses=False,
                        max_connections=mas_config.REDIS_MAX_CONNECTIONS,
                        socket_timeout=mas_config.REDIS_SOCKET_TIMEOUT,
                        socket_connect_timeout=mas_config.REDIS_CONNECT_TIMEOUT,
                    )
                    logger.info("Redis连接池初始化完成")
        return self._redis_pool  # type: ignore[return-value]

    async def get_redis_client(self) -> Redis:
        """基于连接池返回Redis客户端实例。"""
        pool = await self.get_redis_pool()
        return Redis(connection_pool=pool)

    async def close_redis(self) -> None:
        """关闭Redis连接池。"""
        async with self._redis_lock:
            if self._redis_pool:
                await self._redis_pool.disconnect()
                self._redis_pool = None
                logger.info("Redis连接池关闭成功")

    async def verify_redis_connection(self) -> bool:
        """测试Redis连通性。"""
        try:
            client = await self.get_redis_client()
            pong = await client.ping()
            if pong:
                logger.info("Redis连接测试成功")
            return bool(pong)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Redis连接测试失败: {exc}")
            return False

    # --- Elasticsearch helpers -------------------------------------------
    async def get_es_client(self) -> AsyncElasticsearch:
        """获取或初始化Elasticsearch客户端。"""
        if self._es_client is None:
            async with self._es_lock:
                if self._es_client is None:
                    logger.info(f"初始化Elasticsearch连接: {mas_config.ELASTICSEARCH_URL}")
                    client_options = {
                        "hosts": mas_config.ELASTICSEARCH_URL,
                        "verify_certs": mas_config.ELASTICSEARCH_VERIFY_CERTS,
                        "max_retries": mas_config.ES_MAX_RETRIES,
                        "retry_on_timeout": True,
                        "request_timeout": mas_config.ES_REQUEST_TIMEOUT,
                    }
                    if mas_config.ELASTICSEARCH_USER and mas_config.ELASTICSEARCH_PASSWORD:
                        client_options["basic_auth"] = (
                            mas_config.ELASTICSEARCH_USER,
                            mas_config.ELASTICSEARCH_PASSWORD,
                        )
                    elif mas_config.ELASTICSEARCH_USER or mas_config.ELASTICSEARCH_PASSWORD:
                        logger.warning("Elasticsearch认证配置不完整，已跳过basic_auth设置")
                    self._es_client = AsyncElasticsearch(**client_options)
                    logger.info("Elasticsearch客户端初始化完成")
        return self._es_client  # type: ignore[return-value]

    async def close_es(self) -> None:
        """关闭Elasticsearch客户端。"""
        async with self._es_lock:
            if self._es_client:
                await self._es_client.close()
                self._es_client = None
                logger.info("Elasticsearch连接关闭成功")

    async def verify_es_connection(self) -> bool:
        """测试Elasticsearch连通性。"""
        try:
            es_client = await self.get_es_client()
            info = await es_client.info()
            version = info.get("version", {}).get("number", "unknown")
            logger.info(f"Elasticsearch连接测试成功 - 版本: {version}")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Elasticsearch连接测试失败: {exc}")
            return False

    # --- Milvus helpers ---------------------------------------------------
    async def ensure_milvus_connection(self) -> None:
        """建立Milvus连接。"""
        if not self._milvus_connected:
            async with self._milvus_lock:
                if not self._milvus_connected:
                    try:
                        logger.info(
                            f"初始化Milvus连接: {mas_config.MILVUS_HOST}:{mas_config.MILVUS_PORT}"
                        )
                        connections.connect(
                            alias="default",
                            host=mas_config.MILVUS_HOST,
                            port=mas_config.MILVUS_PORT,
                        )
                        self._milvus_connected = True
                        logger.info("Milvus连接成功")
                    except MilvusException as exc:
                        logger.error(f"Milvus连接失败: {exc}")
                        raise ConnectionError(f"Failed to connect to Milvus: {exc}") from exc

    async def close_milvus(self) -> None:
        """关闭Milvus连接。"""
        async with self._milvus_lock:
            if self._milvus_connected:
                try:
                    connections.disconnect("default")
                    self._milvus_connected = False
                    logger.info("Milvus连接关闭成功")
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Milvus连接关闭失败: {exc}")

    async def verify_milvus_connection(self) -> bool:
        """测试Milvus连通性。"""
        try:
            await self.ensure_milvus_connection()
            logger.info("Milvus连接测试成功")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Milvus连接测试失败: {exc}")
            return False

    # --- Orchestration ----------------------------------------------------
    async def initialize_all(self) -> None:
        """
        初始化所有已启用的基础设施客户端。

        调用者需自行决定错误策略；当前实现如遇异常将记录日志并继续，
        以保持兼容历史行为。
        """
        await self.verify_db_connection()
        await self.verify_redis_connection()

        # 其他依赖可选组件：遇到错误时仅记录，避免影响主要服务。
        await self._init_optional_services()

    async def shutdown_all(self) -> None:
        """关闭所有注册的客户端。"""
        await self.close_db()
        await self.close_redis()
        await self.close_es()
        await self.close_milvus()

    async def _init_optional_services(self) -> None:
        """初始化非强制组件（Elasticsearch / Milvus）。"""
        try:
            await self.verify_es_connection()
        except Exception:
            # verify_es_connection 已记录错误，这里避免向外传播
            pass

        try:
            await self.verify_milvus_connection()
        except Exception:
            # verify_milvus_connection 已记录错误
            pass

    # --- Utility context managers ----------------------------------------
    @asynccontextmanager
    async def db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """提供数据库会话上下文管理。"""
        session_factory = await self.get_db_session_factory()
        session = session_factory()
        try:
            yield session
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.error(f"数据库操作失败，本次操作已取消: {exc}")
            raise
        finally:
            await session.close()


# 全局注册表实例
infra_registry = InfraRegistry()


async def initialize_infra() -> None:
    """统一初始化基础设施客户端。"""
    await infra_registry.initialize_all()


async def shutdown_infra() -> None:
    """统一关闭基础设施客户端。"""
    await infra_registry.shutdown_all()


__all__ = [
    "infra_registry",
    "initialize_infra",
    "shutdown_infra",
]
