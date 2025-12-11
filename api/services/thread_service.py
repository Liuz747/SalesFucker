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
from libs.factory import infra_registry
from repositories.thread_repo import ThreadRepository, Thread
from schemas import ThreadPayload
from schemas.exceptions import ThreadNotFoundException, TenantValidationException
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
        """
        try:
            thread_orm = thread.to_orm()
            
            async with database_session() as session:
                # 1. 立即写入数据库
                thread_orm = await ThreadRepository.insert_thread(thread_orm, session)

            if thread_orm:
                # 2. 异步更新Redis缓存
                redis_client = infra_registry.get_cached_clients().redis
                thread_model = Thread.to_model(thread_orm)
                asyncio.create_task(
                    ThreadRepository.update_thread_cache(thread_model, redis_client)
                )

                
                logger.debug(f"线程写入redis缓存成功: {thread_model.thread_id}")
                return thread_model.thread_id
            
            return None

        except Exception as e:
            logger.error(f"线程创建失败: {e}")
            raise
    
    @staticmethod
    async def get_thread(thread_id: UUID) -> Optional[Thread]:
        """
        获取线程
        
        性能目标: < 10ms 响应时间
        """
        try:
            # 直接获取Redis客户端，使用连接池
            redis_client = infra_registry.get_cached_clients().redis
            
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
    async def update_thread_status(thread: Thread) -> Thread:
        """更新线程"""
        try:
            thread_orm = thread.to_orm()
            
            # 立即更新数据库
            async with database_session() as session:
                updated_thread_orm = await ThreadRepository.update_thread_model(thread_orm, session)

            # 直接获取Redis客户端，使用连接池
            redis_client = infra_registry.get_cached_clients().redis

            thread_model = Thread.to_model(updated_thread_orm)

            # 异步更新Redis缓存
            asyncio.create_task(
                ThreadRepository.update_thread_cache(thread_model, redis_client)
            )
            
            return thread_model
            
        except Exception as e:
            logger.error(f"线程更新失败: {e}")
            raise

    @staticmethod
    async def update_thread_info(tenant_id: str, thread_id: UUID, request: ThreadPayload) -> Thread:
        """
        更新线程客户会话信息

        仅更新请求中提供的非空字段（部分更新），支持更新客户基本信息和消费状态。
        更新完成后异步刷新Redis缓存。

        参数:
            tenant_id: 租户标识符，用于验证线程归属
            thread_id: 线程标识符
            request: 包含待更新字段的请求体，仅更新非空字段

        返回:
            Thread: 更新后的线程业务模型

        异常:
            ThreadNotFoundException: 线程不存在
            TenantValidationException: 租户ID不匹配，无权访问此线程
        """
        try:
            async with database_session() as session:
                # 查询线程是否存在
                thread_orm = await ThreadRepository.get_thread(thread_id, session)
                if not thread_orm:
                    raise ThreadNotFoundException(thread_id)

                # 验证租户归属权限
                if thread_orm.tenant_id != tenant_id:
                    raise TenantValidationException(tenant_id, "租户ID不匹配，无法访问此线程")

                # 部分更新：仅更新请求中提供的字段
                updated_thread = request.model_dump(exclude_unset=True)
                for key, value in updated_thread.items():
                    setattr(thread_orm, key, value)

                updated_thread_orm = await ThreadRepository.update_thread_model(thread_orm, session)
                logger.info(f"线程更新成功: {updated_thread_orm.thread_id}")

                thread_model = Thread.to_model(updated_thread_orm)

            # 异步刷新Redis缓存
            redis_client = infra_registry.get_cached_clients().redis
            asyncio.create_task(ThreadRepository.update_thread_cache(thread_model, redis_client))

            return thread_model

        except ThreadNotFoundException as e:
            logger.error(f"线程不存在: {e}")
            raise
        except TenantValidationException as e:
            logger.error(f"租户ID不匹配: {e}")
            raise
        except Exception as e:
            logger.error(f"线程更新失败: {e}")
            raise
