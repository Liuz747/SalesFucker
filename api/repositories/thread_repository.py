"""
高性能线程存储库

该模块实现混合存储策略，针对云端PostgreSQL数据库的高延迟问题进行优化。
采用缓存+数据库二级存储架构，确保最佳性能和数据安全性。

存储架构:
1. Redis缓存 - 跨实例共享 < 10ms 访问速度  
2. PostgreSQL - 持久化存储，异步写入
"""

from typing import Optional

import msgpack
from uuid import UUID
from redis import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import mas_config
from models import ThreadOrm
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "ThreadRepository")


class ThreadRepository:
    """
    高性能线程存储库
    
    实现混合存储策略：
    1. Redis缓存 - 分布式共享 (< 10ms)
    2. PostgreSQL - 持久化存储 (异步写入)
    """
        
    @staticmethod
    async def get_thread(thread_id: str, session: AsyncSession) -> Optional[ThreadOrm]:
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
    async def insert_thread(thread: ThreadOrm, session: AsyncSession) -> UUID:
        """
        创建线程数据库模型
        """
        try:
            session.add(thread)
            logger.debug(f"创建线程: {thread.thread_id}")
            return thread.id
        except Exception as e:
            logger.error(f"创建线程数据库模型失败: {thread.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread(thread: ThreadOrm, session: AsyncSession) -> UUID:
        """
        更新线程数据库模型
        """
        try:
            session.merge(thread)
            logger.debug(f"更新线程: {thread.thread_id}")
            return thread.id
        except Exception as e:
            logger.error(f"更新线程数据库模型失败: {thread.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_thread(thread_id: str, session: AsyncSession):
        """
        删除线程数据库模型
        """
        try:
            thread = await session.get(ThreadOrm, thread_id)
            if not thread:
                raise ValueError(f"线程不存在: {thread_id}")
            
            thread.is_active = False
            thread.updated_at = get_current_datetime()

            logger.debug(f"删除线程: {thread_id}")

        except Exception as e:
            logger.error(f"删除线程数据库模型失败: {thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_field(thread_id: str, value: dict, session: AsyncSession) -> bool:
        """
        更新线程数据库模型字段
        """
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
    async def update_thread_cache(thread_data: dict, redis_client: Redis):
        """
        更新线程缓存
        """
        try:
            redis_key = f"thread:{thread_data['thread_id']}"

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(thread_data),
            )
            logger.debug(f"更新线程缓存: {thread_data['thread_id']}")

        except Exception as e:
            logger.error(f"更新线程缓存失败: {thread_data['thread_id']}, 错误: {e}")
            raise

    @staticmethod
    async def get_thread_cache(thread_id: str, redis_client: Redis) -> Optional[dict]:
        """
        获取线程缓存
        """
        try:
            redis_key = f"thread:{thread_id}"
            redis_data = await redis_client.get(redis_key)

            if redis_data:
                return msgpack.unpackb(redis_data, raw=False)
            return None
        except Exception as e:
            logger.error(f"获取线程缓存失败: {thread_id}, 错误: {e}")
            raise