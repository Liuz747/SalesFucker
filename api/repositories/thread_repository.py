"""
高性能线程存储库

该模块实现混合存储策略，针对云端PostgreSQL数据库的高延迟问题进行优化。
采用缓存+数据库二级存储架构，确保最佳性能和数据安全性。

存储架构:
1. Redis缓存 - 跨实例共享 < 10ms 访问速度  
2. PostgreSQL - 持久化存储，异步写入
"""

import asyncio
from typing import Optional

import msgpack

from config import mas_config
from utils import get_component_logger, get_current_datetime, to_isoformat
from controllers.workspace.conversation.schema import ThreadModel
from infra.cache.redis_client import get_redis_client
from services.thread_service import ThreadService


class ThreadRepository:
    """
    高性能线程存储库
    
    实现混合存储策略：
    1. Redis缓存 - 分布式共享 (< 10ms)
    2. PostgreSQL - 持久化存储 (异步写入)
    """
    
    def __init__(self):
        self.logger = get_component_logger(__name__, "ThreadRepository")
        
        # Redis客户端
        self._redis_client = None
        
        # 缓存配置
        self.redis_ttl = mas_config.REDIS_TTL
    
    async def initialize(self):
        """初始化存储库"""
        try:
            self._redis_client = await get_redis_client()
            self.logger.info("Redis连接初始化完成")
        except Exception as e:
            self.logger.error(f"Redis连接初始化失败: {e}")
            raise
        
        self.logger.info("线程存储库初始化完成")
    
    async def create_thread(self, thread: ThreadModel) -> ThreadModel:
        """
        创建线程 - 优化性能策略
        
        性能目标: < 5ms 响应时间
        """
        try:
            # 1. 立即更新Redis缓存
            await self._update_redis_cache(thread)
            
            # 2. 异步写入数据库
            asyncio.create_task(ThreadService.save(thread))
            
            self.logger.debug(f"线程创建成功: {thread.thread_id}")
            return thread
            
        except Exception as e:
            self.logger.error(f"线程创建失败: {e}")
            raise
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadModel]:
        """
        获取线程 - Redis缓存策略
        
        性能目标: < 10ms 响应时间
        """
        try:
            # 1. Level 1: Redis缓存 (< 10ms)
            thread = await self._get_from_redis(thread_id)
            if thread:
                return thread
            
            # 2. Level 2: 数据库查询
            thread = await ThreadService.query(thread_id)
            if thread:
                # 异步更新缓存
                asyncio.create_task(self._update_redis_cache(thread))
                return thread
            
            return None
            
        except Exception as e:
            self.logger.error(f"线程获取失败: {e}")
            return None
    
    async def update_thread(self, thread: ThreadModel) -> ThreadModel:
        """更新线程"""
        try:
            # 更新时间戳
            thread.updated_at = get_current_datetime()
            
            # 立即更新Redis缓存
            await self._update_redis_cache(thread)
            
            # 异步写入数据库
            asyncio.create_task(ThreadService.save(thread))
            
            return thread
            
        except Exception as e:
            self.logger.error(f"线程更新失败: {e}")
            raise
    
    async def _get_from_redis(self, thread_id: str) -> Optional[ThreadModel]:
        """从Redis缓存获取线程"""
        if not self._redis_client:
            return None
            
        try:
            redis_key = f"thread:{thread_id}"
            redis_data = await self._redis_client.get(redis_key)
            
            if redis_data:
                thread_dict = msgpack.unpackb(redis_data, raw=False)
                return ThreadModel(**thread_dict)
                
        except Exception as e:
            self.logger.warning(f"Redis查询失败: {e}")
        
        return None
    
    async def _update_redis_cache(self, thread: ThreadModel):
        """异步更新Redis缓存"""
        if not self._redis_client:
            return
            
        try:
            redis_key = f"thread:{thread.thread_id}"
            thread_dict = thread.model_dump()
            # 序列化datetime对象
            thread_dict["created_at"] = to_isoformat(thread.created_at)
            thread_dict["updated_at"] = to_isoformat(thread.updated_at)
            
            await self._redis_client.setex(
                redis_key,
                self.redis_ttl,
                msgpack.packb(thread_dict)
            )
            
        except Exception as e:
            self.logger.warning(f"Redis更新失败: {e}")
    
    async def cleanup(self):
        """清理资源"""
        # 清理Redis客户端引用（共享连接池由应用层管理）
        self._redis_client = None
        
        self.logger.info("线程存储库已清理")


# 全局单例实例
_thread_repository: Optional[ThreadRepository] = None


async def get_thread_repository() -> ThreadRepository:
    """获取线程存储库单例实例"""
    global _thread_repository
    
    if _thread_repository is None:
        _thread_repository = ThreadRepository()
        await _thread_repository.initialize()
    
    return _thread_repository