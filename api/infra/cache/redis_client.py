"""
Redis客户端工厂
"""
from typing import Optional

from redis.asyncio import Redis, ConnectionPool

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)

_redis_pool: Optional[ConnectionPool] = None


async def get_redis_client() -> Redis:
    """
    异步获取Redis客户端
    """
    global _redis_pool

    if _redis_pool is None:
        logger.info(f"初始化Redis连接: {mas_config.REDIS_HOST}")
        _redis_pool = ConnectionPool.from_url(
            mas_config.redis_url,
            decode_responses=False,
            max_connections=mas_config.REDIS_MAX_CONNECTIONS,
            socket_timeout=mas_config.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=mas_config.REDIS_CONNECT_TIMEOUT
        )
    logger.info("Redis引擎初始化完成")
    return Redis(connection_pool=_redis_pool)


async def close_redis_client():
    """
    关闭Redis客户端连接
    """
    global _redis_pool

    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None

        logger.info("Redis连接池关闭成功")


async def test_redis_connection():
    """测试Redis连接"""
    try:
        redis_client = await get_redis_client()
        # 使用ping命令测试连接
        pong = await redis_client.ping()
        if pong:
            logger.info("Redis连接测试成功")
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
