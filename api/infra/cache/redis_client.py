"""
Redis客户端工厂
"""
from typing import Optional

from redis.asyncio import Redis, ConnectionPool

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)

_redis_pool: Optional[ConnectionPool] = None

async def init_redis_pool() -> ConnectionPool:
    """初始化Redis连接池"""
    global _redis_pool

    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            mas_config.redis_url,
            decode_responses=False,
            max_connections=mas_config.REDIS_MAX_CONNECTIONS,
            socket_timeout=mas_config.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=mas_config.REDIS_CONNECT_TIMEOUT
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


async def test_redis_connection() -> bool:
    """
    测试Redis连接
    
    返回:
        bool: 连接是否成功
    """
    try:
        redis_client = await get_redis_client()
        # 使用ping命令测试连接
        pong = await redis_client.ping()
        if pong:
            logger.info("Redis连接测试成功")
            return True
        return False
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
        return False