"""
线程业务服务层

该模块实现线程相关的业务逻辑和协调功能。
遵循Service模式，协调缓存和数据库操作，提供高性能的线程管理服务。

核心功能:
- 线程业务逻辑处理和工作流协调
- 缓存+数据库混合存储策略管理
- Redis缓存和PostgreSQL数据库的协调
- 异步性能优化（缓存优先，数据库异步）
"""

import asyncio
from uuid import UUID
from typing import Optional

from models import ThreadOrm
from repositories.thread_repository import ThreadRepository
from controllers.workspace.conversation.model import Thread
from infra.db.connection import database_session
from infra.cache.redis_client import get_redis_client
from utils import get_component_logger

logger = get_component_logger(__name__, "ThreadService")


class ThreadService:
    """
    线程业务服务层
    
    实现高性能线程管理的业务逻辑:
    1. 缓存优先策略 - Redis < 10ms 响应时间
    2. 数据库持久化 - PostgreSQL 异步写入
    3. 依赖管理 - Redis客户端生命周期管理
    4. 业务协调 - 缓存和数据库操作的统一协调
    """

    def __init__(self):
        # Redis客户端
        self._redis_client = None
    
    async def dispatch(self):
        """初始化服务依赖（Redis客户端连接）"""
        try:
            self._redis_client = await get_redis_client()
            # 测试Redis连接
            await self._redis_client.ping()
            logger.info("Redis连接初始化完成")
        except Exception as e:
            logger.error(f"Redis连接初始化失败: {e}")
            raise
        
        logger.info("线程服务初始化完成")
    
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
                thread_model = Thread.from_orm(thread)
                asyncio.create_task(ThreadRepository.update_thread_cache(
                    thread_model,
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
            thread_model = await ThreadRepository.get_thread_cache(thread_id, self._redis_client)
            if thread_model:

                return thread_model.to_orm()
            
            # Level 2: 数据库查询
            async with database_session() as session:
                thread_orm = await ThreadRepository.get_thread(thread_id, session)
            if thread_orm:
                # 异步更新缓存
                thread_model = Thread.from_orm(thread_orm)
                asyncio.create_task(ThreadRepository.update_thread_cache(thread_model, self._redis_client))
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

            # 异步更新Redis缓存
            thread_model = Thread.from_orm(thread_orm)
            asyncio.create_task(ThreadRepository.update_thread_cache(
                thread_model,
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
        
        logger.info("线程服务已清理")