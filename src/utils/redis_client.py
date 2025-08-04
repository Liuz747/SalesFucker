"""
Redis客户端工厂
"""
import asyncio
import redis.asyncio as redis
from typing import Optional
from config.settings import settings


class RedisClientManager:
    """Redis客户端管理器"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def get_client(self) -> redis.Redis:
        """获取Redis客户端实例"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = redis.from_url(
                        settings.redis_url, 
                        decode_responses=True
                    )
        return self._client
    
    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局Redis客户端管理器
_redis_manager = RedisClientManager()


def get_redis_client() -> redis.Redis:
    """
    获取Redis客户端
    
    返回一个Redis客户端实例，使用默认配置
    """
    return redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis_client_async() -> redis.Redis:
    """
    异步获取Redis客户端
    """
    return await _redis_manager.get_client()


async def close_redis_client():
    """
    关闭Redis客户端连接
    """
    await _redis_manager.close()