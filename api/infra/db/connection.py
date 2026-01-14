"""
数据库连接管理

该模块提供PostgreSQL数据库连接池和会话管理功能。
支持异步操作和连接池优化。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__, "Database")


async def create_db_engine() -> AsyncEngine:
    """
    创建数据库引擎实例

    返回:
        AsyncEngine: SQLAlchemy异步引擎
    """
    return create_async_engine(
        mas_config.postgres_url,
        # 连接池配置
        pool_size=mas_config.SQLALCHEMY_POOL_SIZE,
        max_overflow=mas_config.SQLALCHEMY_MAX_OVERFLOW,
        pool_pre_ping=mas_config.SQLALCHEMY_POOL_PRE_PING,
        pool_recycle=mas_config.SQLALCHEMY_POOL_RECYCLE,
        connect_args={
            "command_timeout": mas_config.SQLALCHEMY_COMMAND_TIMEOUT,
            "server_settings": {
                "application_name": mas_config.APP_NAME,
            }
        },
        echo=mas_config.SQLALCHEMY_ECHO,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    创建会话工厂

    参数:
        engine: 数据库引擎实例

    返回:
        async_sessionmaker: 会话工厂
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False
    )


async def test_db_connection(engine: AsyncEngine) -> bool:
    """
    测试数据库连接

    参数:
        engine: 数据库引擎实例

    返回:
        bool: 连接是否成功
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
        return row[0] == 1
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False


async def close_engine(engine: AsyncEngine):
    """
    关闭数据库引擎

    参数:
        engine: 数据库引擎实例
    """
    await engine.dispose()
    logger.info("数据库连接已关闭")
