"""
Redis客户端工厂
"""

from redis.asyncio import Redis, ConnectionPool

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)


async def create_redis_client() -> Redis:
    """
    创建Redis客户端实例

    创建连接池并返回Redis客户端。

    返回:
        Redis: Redis异步客户端实例
    """
    pool = ConnectionPool.from_url(
        mas_config.redis_url,
        decode_responses=False,
        max_connections=mas_config.REDIS_MAX_CONNECTIONS,
        socket_timeout=mas_config.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=mas_config.REDIS_CONNECT_TIMEOUT
    )
    return Redis(connection_pool=pool)


async def test_redis_connection(client: Redis) -> bool:
    """
    测试Redis连接

    参数:
        client: Redis客户端实例

    返回:
        bool: 连接是否成功
    """
    try:
        return await client.ping()
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
        return False


async def close_redis_client(client: Redis):
    """
    关闭Redis客户端连接

    参数:
        client: Redis客户端实例
    """
    await client.aclose(close_connection_pool=True)
    logger.info("Redis连接池关闭成功")
