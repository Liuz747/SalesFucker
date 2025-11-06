"""
线程数据访问存储库

该模块提供纯粹的线程数据访问操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作，支持数据库和缓存的独立访问。

核心功能:
- 线程数据库CRUD操作（PostgreSQL）
- 线程缓存操作（Redis）  
- 纯数据访问，无业务逻辑
- 依赖注入，支持外部会话管理
"""

from uuid import UUID
from typing import Optional

import msgpack
from redis import Redis
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import mas_config
from models import ThreadOrm, Thread
from utils import get_component_logger

logger = get_component_logger(__name__, "ThreadRepository")


class ThreadRepository:
    """
    提供数据访问操作:
    1. 数据库操作 - PostgreSQL CRUD操作，依赖注入AsyncSession
    2. 缓存操作 - Redis读写操作，依赖注入Redis客户端
    3. 无业务逻辑 - 仅处理数据持久化和检索
    4. 静态方法 - 无状态设计，支持依赖注入
    """
        
    @staticmethod
    async def get_thread(thread_id: UUID, session: AsyncSession) -> Optional[ThreadOrm]:
        """
        获取线程数据库模型
        
        参数:
            session: 数据库会话
            thread_id: 线程ID
            
        返回:
            ThreadOrm: 线程数据库模型，不存在则返回None
        """
        try:
            stmt = select(ThreadOrm).where(ThreadOrm.thread_id == thread_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取线程数据库模型失败: {thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_thread(thread: ThreadOrm, session: AsyncSession) -> Optional[ThreadOrm]:
        """创建线程数据库模型"""
        try:
            session.add(thread)
            return thread
        except Exception as e:
            logger.error(f"创建线程数据库模型失败: {thread.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_model(thread: ThreadOrm, session: AsyncSession) -> ThreadOrm:
        """更新线程数据库模型"""
        try:
            logger.debug(f"更新线程: {thread.thread_id}")
            return await session.merge(thread)
        except Exception as e:
            logger.error(f"更新线程数据库模型失败: {thread.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_thread(thread_id: UUID, session: AsyncSession):
        """删除线程数据库模型"""
        try:
            thread = await session.get(ThreadOrm, thread_id)
            if not thread:
                raise ValueError(f"线程不存在: {thread_id}")
            
            thread.is_active = False
            thread.updated_at = func.now()
            logger.debug(f"删除线程: {thread_id}")

        except Exception as e:
            logger.error(f"删除线程数据库模型失败: {thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_field(thread_id: UUID, value: dict, session: AsyncSession) -> bool:
        """更新线程数据库模型字段"""
        try:
            stmt = (
                update(ThreadOrm)
                .where(ThreadOrm.thread_id == thread_id)
                .values(**value)
            )
            result = await session.execute(stmt)
            
            if result.rowcount > 0:
                logger.debug(f"更新线程字段: {thread_id}, 值: {value}")
            else:
                logger.warning(f"线程不存在，无法更新: {thread_id}")
                
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新线程数据库模型字段失败: {thread_id}, 值: {value}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_cache(thread_model: Thread, redis_client: Redis):
        """更新线程缓存"""
        try:
            redis_key = f"thread:{thread_model.thread_id}"
            thread_data = thread_model.model_dump(mode='json')

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(thread_data),
            )
            logger.debug(f"更新线程缓存: {thread_model.thread_id}")

        except Exception as e:
            logger.error(f"更新线程缓存失败: {thread_model.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_thread_cache(thread_id: UUID, redis_client: Redis) -> Optional[Thread]:
        """获取线程缓存"""
        try:
            redis_key = f"thread:{str(thread_id)}"
            redis_data = await redis_client.get(redis_key)

            if redis_data:
                thread_dict = msgpack.unpackb(redis_data, raw=False)
                return Thread(**thread_dict)
            return None
        except Exception as e:
            logger.error(f"获取线程缓存失败: {thread_id}, 错误: {e}")
            raise
