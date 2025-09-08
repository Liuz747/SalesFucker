"""
线程数据库操作层

该模块提供纯粹的线程数据库CRUD操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作。

核心功能:
- 线程配置的数据库CRUD操作
- 数据库健康检查
"""

import asyncio
from uuid import UUID
from typing import Optional

import msgpack

from models import ThreadOrm
from repositories.thread_repository import ThreadRepository
from infra.db.connection import database_session
from infra.cache.redis_client import get_redis_client
from utils import get_component_logger, to_isoformat, from_isoformat

logger = get_component_logger(__name__, "ThreadService")


class ThreadService:

    def __init__(self):
        # Redis客户端
        self._redis_client = None
    
    async def dispatch(self):
        """初始化存储库"""
        try:
            self._redis_client = await get_redis_client()
            # 测试Redis连接
            await self._redis_client.ping()
            logger.info("Redis连接初始化完成")
        except Exception as e:
            logger.error(f"Redis连接初始化失败: {e}")
            raise
        
        logger.info("线程存储库初始化完成")
    
    async def create_thread(self, thread: ThreadOrm) -> UUID:
        """
        创建线程 - 优化性能策略
        
        参数:
            thread: 线程ORM对象
        
        性能目标: < 5ms 响应时间
        """
        try:
            async with database_session() as session:
                # 1. 立即写入数据库
                thread_id  = await ThreadRepository.insert_thread(thread, session)

            if thread_id:
                # 2. 异步更新Redis缓存
                thread_data = {
                    "thread_id": thread.thread_id,
                    "assistant_id": thread.assistant_id,
                    "tenant_id": thread.tenant_id,
                    "status": thread.status,
                    "created_at": to_isoformat(thread.created_at),
                    "updated_at": to_isoformat(thread.updated_at),
                }
                asyncio.create_task(ThreadRepository.update_thread_cache(
                    thread_data,
                    self._redis_client
                ))
                
                logger.debug(f"线程写入redis缓存成功: {thread.thread_id}")
                return thread_id
            else:
                logger.error(f"线程写入redis缓存失败: {thread.thread_id}")
                raise RuntimeError(f"线程写入redis缓存失败: {thread.thread_id}")

        except Exception as e:
            logger.error(f"线程创建失败: {e}")
            raise
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadOrm]:
        """
        获取线程 - Redis缓存策略
        
        性能目标: < 10ms 响应时间
        """
        try:
            # Level 1: Redis缓存 (< 10ms)
            thread = await ThreadRepository.get_thread_cache(thread_id, self._redis_client)
            if thread:
                thread['created_at'] = from_isoformat(thread['created_at'])
                thread['updated_at'] = from_isoformat(thread['updated_at'])
                return ThreadOrm(**thread)
            
            # Level 2: 数据库查询
            async with database_session() as session:
                thread_orm = await ThreadRepository.get_thread(thread_id, session)
            if thread_orm:
                # 异步更新缓存
                thread_data = {
                    "thread_id": thread_orm.thread_id,
                    "assistant_id": thread_orm.assistant_id,
                    "tenant_id": thread_orm.tenant_id,
                    "status": thread_orm.status,
                    "created_at": to_isoformat(thread_orm.created_at),
                    "updated_at": to_isoformat(thread_orm.updated_at),
                }
                asyncio.create_task(ThreadRepository.update_thread_cache(thread_data, self._redis_client))
                return thread_orm
            
            return None
            
        except Exception as e:
            logger.error(f"线程获取失败: {e}")
            return None
    
    async def update_thread(self, thread_orm: ThreadOrm) -> ThreadOrm:
        """更新线程"""
        try:
            # 立即更新数据库
            async with database_session() as session:
                await ThreadRepository.update_thread(thread_orm, session)

            thread_data = {
                "thread_id": thread_orm.thread_id,
                "assistant_id": thread_orm.assistant_id,
                "tenant_id": thread_orm.tenant_id,
                "status": thread_orm.status,
                "created_at": to_isoformat(thread_orm.created_at),
                "updated_at": to_isoformat(thread_orm.updated_at),
            }
            
            # 异步更新Redis缓存
            asyncio.create_task(ThreadRepository.update_thread_cache(
                thread_data,
                self._redis_client
            ))
            
            return thread_orm
            
        except Exception as e:
            logger.error(f"线程更新失败: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        # 清理Redis客户端引用（共享连接池由应用层管理）
        self._redis_client = None
        
        logger.info("线程存储库已清理")