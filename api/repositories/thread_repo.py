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

from collections.abc import Sequence
from datetime import timedelta
from typing import Optional
from uuid import UUID

import msgpack
from redis.asyncio import Redis
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from config import mas_config
from libs.types import ThreadStatus
from models import ThreadOrm, Thread
from utils import get_component_logger, get_current_datetime

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
    async def insert_thread(thread: ThreadOrm, session: AsyncSession) -> ThreadOrm:
        """创建线程数据库模型"""
        try:
            session.add(thread)
            # 刷新以获取数据库生成的值（如 thread_id, created_at, updated_at）
            await session.flush()
            await session.refresh(thread)
            return thread
        except Exception as e:
            logger.error(f"创建线程数据库模型失败: {thread.thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_model(thread: ThreadOrm, session: AsyncSession) -> ThreadOrm:
        """更新线程数据库模型"""
        try:
            thread.updated_at = func.now()
            logger.debug(f"更新线程: {thread.thread_id}")
            merged_thread = await session.merge(thread)
            # 刷新以获取数据库生成的值（如 updated_at）
            await session.flush()
            await session.refresh(merged_thread)
            return merged_thread
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
    async def update_thread_field(thread_id: UUID, value: dict, session: AsyncSession) -> Optional[ThreadOrm]:
        """更新线程数据库模型字段"""
        try:
            stmt = (
                update(ThreadOrm)
                .where(ThreadOrm.thread_id == thread_id)
                .values(updated_at=func.now(), **value)
                .returning(ThreadOrm)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"更新线程数据库模型字段失败: {thread_id}, 值: {value}, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_cache(thread_model: Thread, redis_client: Redis):
        """更新线程缓存"""
        try:
            redis_key = f"thread:{str(thread_model.thread_id)}"
            thread_data = thread_model.model_dump(mode='json')

            # TODO: 更新Redis方法，setex已经进入废弃流程
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

    @staticmethod
    async def batch_delete_cache(thread_ids: Sequence[UUID], redis_client: Redis):
        """
        批量删除线程缓存

        参数:
            thread_ids: 线程ID列表
            redis_client: Redis客户端
        """
        try:
            if not thread_ids:
                return

            # 使用pipeline批量删除
            async with redis_client.pipeline(transaction=True) as pipeline:
                for thread_id in thread_ids:
                    redis_key = f"thread:{str(thread_id)}"
                    await pipeline.delete(redis_key)
                await pipeline.execute()
                logger.debug(f"批量删除线程缓存: {len(thread_ids)} 个线程")

        except Exception as e:
            logger.error(f"批量删除线程缓存失败: 错误: {e}")

    @staticmethod
    async def get_inactive_threads(session: AsyncSession) -> Sequence[ThreadOrm]:
        """
        查询不活跃线程（用于唤醒工作流）

        参数:
            session: 数据库会话

        返回:
            不活跃线程列表
        """
        try:
            # 临时测试修改
            # threshold = get_current_datetime() - timedelta(days=mas_config.INACTIVE_INTERVAL_DAYS)
            threshold = get_current_datetime() - timedelta(hours=mas_config.INACTIVE_INTERVAL_DAYS)

            stmt = select(ThreadOrm).where(
                and_(
                    ThreadOrm.enable_takeover,
                    ThreadOrm.enable_trigger,
                    ThreadOrm.status != ThreadStatus.BUSY,
                    # 未超过最大尝试次数
                    ThreadOrm.awakening_attempt_count < mas_config.MAX_AWAKENING_ATTEMPTS,
                    # 满足不活跃条件：指定天数未活动或从未互动
                    or_(
                        ThreadOrm.last_interaction_at.is_(None),  # 从未互动
                        ThreadOrm.last_interaction_at < threshold  # 超过指定天数未互动
                    )
                )
            ).order_by(ThreadOrm.last_interaction_at.asc()).limit(mas_config.AWAKENING_BATCH_SIZE)

            result = await session.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"查询不活跃线程失败, 错误: {e}")
            raise

    @staticmethod
    async def update_thread_status(thread_id: UUID, status: ThreadStatus, session: AsyncSession) -> bool:
        """
        更新线程状态和最后互动时间

        参数:
            thread_id: 线程ID
            status: 状态
            session: 数据库会话

        返回:
            bool: 是否更新成功
        """
        try:
            stmt = (
                update(ThreadOrm)
                .where(ThreadOrm.thread_id == thread_id)
                .values(
                    status=status,
                    last_interaction_at=func.now(),
                    updated_at=func.now()
                )
            )

            result = await session.execute(stmt)
            return result.rowcount > 0

        except Exception as e:
            logger.error(f"更新线程状态失败: thread_id={thread_id}, status={status}, 错误: {e}")
            raise

    @staticmethod
    async def increment_awakening_attempt(thread_id: UUID, session: AsyncSession) -> bool:
        """
        增加线程的唤醒尝试计数并更新最后互动时间

        参数:
            thread_id: 线程ID
            session: 数据库会话

        返回:
            bool: 是否更新成功
        """
        try:
            stmt = (
                update(ThreadOrm)
                .where(ThreadOrm.thread_id == thread_id)
                .values(
                    awakening_attempt_count=ThreadOrm.awakening_attempt_count + 1,
                    last_interaction_at=func.now(),
                    updated_at=func.now()
                )
            )

            result = await session.execute(stmt)
            return result.rowcount > 0

        except Exception as e:
            logger.error(f"增加唤醒计数失败: thread_id={thread_id}, 错误: {e}")
            raise

    @staticmethod
    async def bulk_update_threads(
        tenant_id: str,
        thread_ids: list[UUID],
        set_updates: dict,
        session: AsyncSession
    ) -> Sequence[UUID]:
        """
        批量更新线程字段

        参数:
            tenant_id: 租户ID，用于验证线程归属
            thread_ids: 要更新的线程ID列表
            set_updates: 要更新的字段字典
            session: 数据库会话

        返回:
            Sequence: 成功的线程ID列表
        """
        try:
            # 批量更新有效的线程
            stmt = (
                update(ThreadOrm)
                .where(
                    ThreadOrm.thread_id.in_(thread_ids),
                    ThreadOrm.tenant_id == tenant_id,
                )
                .values(updated_at=func.now(), **set_updates)
                .returning(ThreadOrm.thread_id)
            )

            result = await session.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"批量更新线程失败: 错误: {e}")
            raise
