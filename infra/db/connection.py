"""
数据库连接管理

该模块提供PostgreSQL数据库连接池和会话管理功能。
支持异步操作和连接池优化。
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from config import settings
from utils import get_component_logger

logger = get_component_logger(__name__, "Database")

# 全局引擎实例
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def get_database_engine() -> AsyncEngine:
    """
    获取数据库引擎实例
    
    返回:
        AsyncEngine: SQLAlchemy异步引擎
    """
    global _engine
    
    if _engine is None:
        logger.info(f"初始化PostgreSQL连接: {settings.DB_HOST}:{settings.DB_PORT}")
        
        _engine = create_async_engine(
            settings.postgres_url,
            # 连接池配置（适合云端部署）
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1小时回收连接
            # 对于云数据库，使用较短的超时
            connect_args={
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "mas-tenant-service",
                }
            },
            echo=settings.DEBUG,  # 开发环境下显示SQL
        )
        
        logger.info("PostgreSQL引擎初始化完成")
    
    return _engine


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    获取会话工厂
    
    返回:
        async_sessionmaker: 会话工厂
    """
    global _session_factory
    
    if _session_factory is None:
        engine = await get_database_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
    
    return _session_factory


async def get_database_session() -> AsyncSession:
    """
    获取数据库会话实例（FastAPI依赖）
    
    返回:
        AsyncSession: 数据库会话
    """
    session_factory = await get_session_factory()
    return session_factory()


@asynccontextmanager
async def database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    数据库会话上下文管理器
    
    用法:
        async with database_session() as session:
            # 数据库操作
            pass
    """
    session_factory = await get_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"数据库操作失败，已回滚: {e}")
        raise
    finally:
        await session.close()


async def close_database_connections():
    """关闭数据库连接"""
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("数据库连接已关闭")


async def test_db_connection() -> bool:
    """
    测试数据库连接
    
    返回:
        bool: 连接是否成功
    """
    try:
        engine = await get_database_engine()
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            row = result.fetchone()
            return row[0] == 1
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False
