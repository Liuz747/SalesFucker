"""
Redis客户端工厂
"""
from typing import Optional

from redis.asyncio import Redis, ConnectionPool

from config import settings
from utils import get_component_logger

logger = get_component_logger(__name__)

_redis_pool: Optional[ConnectionPool] = None

async def init_redis_pool() -> ConnectionPool:
    """初始化Redis连接池"""
    global _redis_pool

    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

        logger.info("Redis连接池初始化成功")

    return _redis_pool


async def get_redis_client() -> Redis:
    """
    异步获取Redis客户端
    """
    pool = await init_redis_pool()
    return Redis(connection_pool=pool)


async def close_redis_client():
    """
    关闭Redis客户端连接
    """
    global _redis_pool
    
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None

        logger.info("Redis连接池关闭成功")