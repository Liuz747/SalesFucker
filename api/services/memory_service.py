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

from core.memory import StorageManager
from libs.types import MemoryType
from schemas.memory_schema import MemoryInsertSummary, MemoryInsertResult
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
