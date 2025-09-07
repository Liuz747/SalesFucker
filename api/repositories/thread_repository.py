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
from utils import get_component_logger, to_isoformat
from infra.cache.redis_client import get_redis_client
from services.thread_service import ThreadService
from models import ThreadOrm


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
            # 测试Redis连接
            await self._redis_client.ping()
            self.logger.info("Redis连接初始化完成")
        except Exception as e:
            self.logger.error(f"Redis连接初始化失败: {e}")
            raise
        
        self.logger.info("线程存储库初始化完成")
    
    async def create_thread(self, thread_orm: ThreadOrm) -> ThreadOrm:
        """
        创建线程 - 优化性能策略
        
        参数:
            thread_orm: 线程ORM对象
            
        返回:
            ThreadOrm: 创建的线程ORM对象
        
        性能目标: < 5ms 响应时间
        """
        try:
            # 1. 立即更新Redis缓存
            await self._update_redis_cache(thread_orm)
            
            # 2. 异步写入数据库
            asyncio.create_task(ThreadService.upsert(
                thread_id=thread_orm.thread_id,
                assistant_id=thread_orm.assistant_id,
                tenant_id=thread_orm.tenant_id
            ))
            
            self.logger.debug(f"线程创建成功: {thread_orm.thread_id}")
            return thread_orm
            
        except Exception as e:
            self.logger.error(f"线程创建失败: {e}")
            raise
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadOrm]:
        """
        获取线程 - Redis缓存策略
        
        性能目标: < 10ms 响应时间
        """
        try:
            # 1. Level 1: Redis缓存 (< 10ms)
            thread_orm = await self._get_from_redis(thread_id)
            if thread_orm:
                return thread_orm
            
            # 2. Level 2: 数据库查询
            thread_orm = await ThreadService.query(thread_id)
            if thread_orm:
                # 异步更新缓存
                asyncio.create_task(self._update_redis_cache(thread_orm))
                return thread_orm
            
            return None
            
        except Exception as e:
            self.logger.error(f"线程获取失败: {e}")
            return None
    
    async def update_thread(self, thread_orm: ThreadOrm) -> ThreadOrm:
        """更新线程"""
        try:
            # 立即更新Redis缓存
            await self._update_redis_cache(thread_orm)
            
            # 异步更新数据库
            asyncio.create_task(ThreadService.update(thread_orm))
            
            return thread_orm
            
        except Exception as e:
            self.logger.error(f"线程更新失败: {e}")
            raise
    
    async def _get_from_redis(self, thread_id: str) -> Optional[ThreadOrm]:
        """从Redis缓存获取线程"""
        if not self._redis_client:
            return None
            
        try:
            redis_key = f"thread:{thread_id}"
            redis_data = await self._redis_client.get(redis_key)
            
            if redis_data:
                thread_dict = msgpack.unpackb(redis_data, raw=False)
                # 反序列化 datetime 字段
                from datetime import datetime
                if 'created_at' in thread_dict and isinstance(thread_dict['created_at'], str):
                    thread_dict['created_at'] = datetime.fromisoformat(thread_dict['created_at'])
                if 'updated_at' in thread_dict and isinstance(thread_dict['updated_at'], str):
                    thread_dict['updated_at'] = datetime.fromisoformat(thread_dict['updated_at'])
                
                # 使用字典解包直接创建 ORM 对象
                return ThreadOrm(**thread_dict)
                
        except Exception as e:
            self.logger.warning(f"Redis查询失败: {e}")
        
        return None
    
    async def _update_redis_cache(self, thread_orm: ThreadOrm):
        """异步更新Redis缓存"""
        if not self._redis_client:
            return
            
        try:
            redis_key = f"thread:{thread_orm.thread_id}"
            # 从 ORM 对象创建缓存数据
            thread_dict = {
                "thread_id": thread_orm.thread_id,
                "assistant_id": thread_orm.assistant_id,
                "tenant_id": thread_orm.tenant_id,
                "status": thread_orm.status,
                "created_at": to_isoformat(thread_orm.created_at),
                "updated_at": to_isoformat(thread_orm.updated_at),
            }
            
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
