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

from infra.db import database_session
from infra.cache import get_redis_client
from repositories.thread_repo import ThreadRepository, Thread
from utils import get_component_logger

logger = get_component_logger(__name__, "ThreadService")


class ThreadService:
    """
    实现高性能线程管理的业务逻辑:
    1. 缓存优先策略 - Redis < 10ms 响应时间
    2. 数据库持久化 - PostgreSQL 异步写入
    3. 业务协调 - 缓存和数据库操作的统一协调
    """
    
    @staticmethod
    async def create_thread(thread: Thread) -> UUID:
        """
        创建线程
        
        参数:
            thread: 线程业务模型
        
        性能目标: < 5ms 响应时间
        """
        try:
            thread_orm = thread.to_orm()
            
            async with database_session() as session:
                # 1. 立即写入数据库
                thread_orm = await ThreadRepository.insert_thread(thread_orm, session)

            if thread_orm:
                # 2. 异步更新Redis缓存
                redis_client = await get_redis_client()
                thread_model = Thread.to_model(thread_orm)
                asyncio.create_task(ThreadRepository.update_thread_cache(
                    thread_model,
                    redis_client
                ))
                
                logger.debug(f"线程写入redis缓存成功: {thread_model.thread_id}")
                return thread_model.thread_id
            
            return None

        except Exception as e:
            logger.error(f"线程创建失败: {e}")
            raise
    
    @staticmethod
    async def get_thread(thread_id: str) -> Optional[Thread]:
        """
        获取线程
        
        性能目标: < 10ms 响应时间
        """
        try:
            # 直接获取Redis客户端，使用连接池
            redis_client = await get_redis_client()
            
            # Level 1: Redis缓存 (< 10ms)
            thread_model = await ThreadRepository.get_thread_cache(thread_id, redis_client)
            if thread_model:
                return thread_model
            
            # Level 2: 数据库查询
            async with database_session() as session:
                thread_orm = await ThreadRepository.get_thread(thread_id, session)
            
            if thread_orm:
                # 异步更新缓存
                thread_model = Thread.to_model(thread_orm)
                asyncio.create_task(ThreadRepository.update_thread_cache(thread_model, redis_client))
                return thread_model
            
            return None
            
        except Exception as e:
            logger.error(f"线程获取失败: {e}")
            return None
    
    @staticmethod
    async def update_thread(thread: Thread) -> bool:
        """更新线程"""
        try:
            thread_orm = thread.to_orm()
            
            # 立即更新数据库
            async with database_session() as session:
                await ThreadRepository.update_thread(thread_orm, session)

            # 直接获取Redis客户端，使用连接池
            redis_client = await get_redis_client()
            # 异步更新Redis缓存
            asyncio.create_task(ThreadRepository.update_thread_cache(
                thread,
                redis_client
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"线程更新失败: {e}")
            raise