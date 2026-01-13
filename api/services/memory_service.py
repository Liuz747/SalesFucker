"""
记忆业务服务层

该模块实现记忆插入相关的业务逻辑，协调StorageManager和其他组件。
遵循Service模式，提供高层次的业务操作。

核心功能:
- 单条和批量记忆插入
- 记忆验证和预处理
- 与StorageManager集成
"""

from typing import Optional
from uuid import UUID

from elasticsearch import NotFoundError

from core.memory import StorageManager
from infra.db import database_session
from libs.exceptions import MemoryNotFoundException, MemoryDeletionException
from libs.types import MemoryType, MessageParams, ThreadStatus
from repositories import ThreadRepository
from schemas import MemoryInsertSummary, MemoryInsertResult
from utils import get_component_logger

logger = get_component_logger(__name__, "MemoryService")


class MemoryService:
    """
    记忆服务 - 提供记忆插入和管理的业务逻辑

    职责:
    1. 调用StorageManager存储记忆
    2. 批量操作的事务性处理
    """

    @staticmethod
    async def insert_memory(
        tenant_id: str,
        thread_id: UUID,
        memories: list[str],
        tags: Optional[list[str]] = None,
    ) -> tuple[list[MemoryInsertResult], MemoryInsertSummary]:
        """
        手动插入记忆

        Args:
            tenant_id: 租户ID
            thread_id: 线程ID
            memories: 记忆列表
            tags: 标签列表

        Returns:
            tuple[list[MemoryInsertResult], MemoryInsertSummary]:
                - results: list[{index, success, memory_id?, error?}]
                - summary: {total, successful, failed}
        """
        results: list[MemoryInsertResult] = []

        try:
            storage_manager = StorageManager()

            # 批量插入记忆
            for idx, memory in enumerate(memories):
                result = await MemoryService.insert_single_memory(
                    idx,
                    storage_manager,
                    tenant_id,
                    thread_id,
                    content=memory,
                    tags=tags
                )
                results.append(result)

            # 计算统计信息
            succeed = sum(1 for r in results if r.success)
            failed = len(results) - succeed

            logger.info(
                f"批量记忆插入完成: thread_id={thread_id}, "
                f"总数={len(results)}, 成功={succeed}, 失败={failed}"
            )

            summary = MemoryInsertSummary(
                total=len(results),
                succeed=succeed,
                failed=failed
            )

            return results, summary

        except Exception as e:
            # 捕获其他未预期的异常
            logger.error(
                f"批量记忆插入发生未预期错误: thread_id={thread_id}, error={e}",
                exc_info=True
            )
            # 如果已经有部分结果，返回它们
            if not results:
                raise
            else:
                succeed = sum(1 for r in results if r.success)
                failed = len(results) - succeed
                logger.warning(f"返回部分插入结果: 成功={succeed}, 失败={failed}")

                summary = MemoryInsertSummary(
                    total=len(results),
                    succeed=succeed,
                    failed=failed
                )
                return results, summary

    @staticmethod
    async def insert_single_memory(
        index: int,
        storage_manager: StorageManager,
        tenant_id: str,
        thread_id: UUID,
        content: str,
        tags: Optional[list[str]] = None
    ) -> MemoryInsertResult:
        """
        插入单条记忆

        Args:
            index: 记忆列表index
            storage_manager: 记忆管理器
            tenant_id: 租户ID
            thread_id: 好友线程ID
            content: 记忆内容
            tags: 标签列表

        Returns:
            MemoryInsertResult: 插入结果
        """

        try:
            memory_id = await storage_manager.add_episodic_memory(
                tenant_id=tenant_id,
                thread_id=thread_id,
                memory_type=MemoryType.EPISODIC,
                content=content,
                tags=tags,
                importance_score=1.0,
                expires_at=None
            )

            logger.info(f"记忆插入成功: memory_id={memory_id}, thread_id={thread_id}")

            return MemoryInsertResult(
                index=index,
                success=True,
                memory_id=memory_id
            )

        except Exception as e:
            logger.error(f"批量插入第{index}条失败: {e}")
            return MemoryInsertResult(
                index=index,
                success=False,
                error=str(e)
            )

    @staticmethod
    async def delete_memory(
        tenant_id: str,
        thread_id: UUID,
        memory_id: str
    ):
        """
        删除指定的记忆

        Args:
            tenant_id: 租户ID
            thread_id: 线程ID
            memory_id: 记忆ID

        Raises:
            MemoryNotFoundException: 记忆不存在或无权访问
            MemoryDeletionException: 删除失败
        """
        try:
            storage_manager = StorageManager()
            await storage_manager.delete_es_memory(
                memory_id,
                tenant_id,
                thread_id
            )

            logger.info(f"记忆删除成功: memory_id={memory_id}")

        except NotFoundError:
            logger.error(f"记忆不存在或无权访问: memory_id={memory_id}")
            raise MemoryNotFoundException(memory_id)
        except Exception as e:
            logger.error(f"记忆删除失败: memory_id={memory_id}, error={e}", exc_info=True)
            raise MemoryDeletionException(reason=str(e))

    @staticmethod
    async def append_messages(
        tenant_id: str,
        thread_id: UUID,
        messages: MessageParams
    ) -> bool:
        """
        追加消息到线程记忆末尾

        将消息按顺序追加到线程的短期记忆（Redis）末尾。
        当消息数量达到阈值时，会自动触发摘要生成并转存到长期记忆（Elasticsearch）。

        参数:
            tenant_id: 租户ID
            thread_id: 线程ID
            messages: 要追加的消息列表

        返回:
            bool
        """
        try:
            # 获取 StorageManager 实例
            storage_manager = StorageManager()

            # 存储消息到短期记忆（会自动触发摘要检查）
            await storage_manager.store_messages(
                tenant_id=tenant_id,
                thread_id=thread_id,
                messages=messages
            )

            # 更新线程的时间戳
            async with database_session() as session:
                await ThreadRepository.update_thread_status(thread_id, ThreadStatus.ACTIVE, session)

            logger.info(f"消息追加成功: thread_id={thread_id}")

            return True

        except Exception as e:
            logger.error(f"消息追加失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
            raise
