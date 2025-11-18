"""
Storage Manager

负责：
- 新消息进入时：写短期记忆
- 判断是否需要摘要 (例如窗口达到 max_messages)
- 调用 LLM 进行摘要
- 写入 Elasticsearch 中长期记忆
- 缩短短期记忆窗口
- 提供 retrieve_context 给 Agent 构建上下文
"""

import asyncio
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

from config import mas_config
from libs.types import MessageParams, Message
from utils import get_component_logger, get_current_datetime
from .conversation_store import ConversationStore
from .elasticsearch_index import ElasticsearchIndex
from .summarize import SummarizationService

logger = get_component_logger(__name__)


class StorageManager:
    """
    混合记忆协调器（Redis + Elasticsearch）

    核心职责：
    1. 短期记忆管理 - Redis 存储最近对话窗口
    2. 长期记忆管理 - Elasticsearch 存储摘要和历史记忆
    3. 记忆转换 - 当短期记忆达到阈值时进行摘要并转存
    4. 上下文检索 - 为 Agent 提供结合短期和长期记忆的完整上下文
    """

    def __init__(self, summary_trigger_threshold: int = 15):
        """
        初始化存储管理器

        Args:
            summary_trigger_threshold: 触发摘要的消息阈值
        """
        self.summary_trigger_threshold = summary_trigger_threshold

        # 初始化子组件
        self.conversation_store = ConversationStore()
        self.elasticsearch_index = ElasticsearchIndex()
        self.summarization_service = SummarizationService()
        self._summary_guard = asyncio.Lock()
        self._active_summaries: set[UUID] = set()

        logger.info("StorageManager initialized")

    async def store_messages(
        self,
        tenant_id: str,
        thread_id: UUID,
        messages: MessageParams
    ) -> int:
        """
        存储新消息到短期记忆并检查是否需要摘要转换

        Args:
            tenant_id: 租户标识
            thread_id: 对话线程ID
            messages: 要存储的消息列表

        Returns:
            int: 存储后的消息总数
        """
        if not messages:
            return 0

        # 写入短期记忆
        non_system_messages = [m for m in messages if m.role != "system"]
        total_messages = await self.conversation_store.append_messages(thread_id, non_system_messages)

        # 检查是否需要摘要转换
        if total_messages >= self.summary_trigger_threshold:
            await self._schedule_summarization(tenant_id, thread_id)

        return total_messages

    async def add_episodic_memory(
        self,
        tenant_id: str,
        thread_id: UUID,
        content: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        存储临时（非对话）记忆到长期记忆

        Args:
            tenant_id: 租户标识
            thread_id: 对话线程ID
            content: 要存储的临时记忆内容
            tags: 可选的标签列表
            metadata: 可选的元数据字典

        Returns:
            str: 存储的临时记忆的ID
        """

        return await self.elasticsearch_index.store_episodic_memory(
            tenant_id=tenant_id,
            thread_id=thread_id,
            content=content,
            tags=tags,
            metadata=metadata
        )

    async def save_assistant_message(self, tenant_id: str, thread_id: UUID, message: str):
        """
        存储助手消息到短期记忆并检查是否需要摘要转换

        Args:
            tenant_id: 租户标识
            thread_id: 对话线程ID
            message: 要存储的助手消息
        """
        msg = [Message(role="assistant", content=message)]
        return await self.store_messages(tenant_id, thread_id, msg)

    async def _schedule_summarization(self, tenant_id: str, thread_id: UUID):
        """确保同一线程仅存在一个并发摘要任务。"""
        async with self._summary_guard:
            if thread_id in self._active_summaries:
                return
            self._active_summaries.add(thread_id)

        async def runner():
            try:
                await self._trigger_summarization(tenant_id, thread_id)
            finally:
                async with self._summary_guard:
                    self._active_summaries.discard(thread_id)

        asyncio.create_task(runner())

    async def _trigger_summarization(self, tenant_id: str, thread_id: UUID) -> bool:
        """触发摘要转换流程"""
        if not self.summarization_service:
            logger.warning("SummarizationService not available, skipping summarization")
            return False

        try:
            # 获取需要摘要的消息
            recent_messages: MessageParams = await self.conversation_store.get_recent(thread_id)

            if not recent_messages:
                return False

            # 生成摘要
            text_block = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_messages])
            summary_content = await self.summarization_service.generate_summary(text_block)
            if not summary_content:
                return False

            # 存储摘要到长期记忆
            await self.elasticsearch_index.store_summary(
                tenant_id=tenant_id,
                thread_id=thread_id,
                content=summary_content,
                memory_type="long_term",
                expires_at=get_current_datetime() + timedelta(days=mas_config.ES_MEMORY_TTL_DAYS),
                tags=["conversation_summary"]
            )

            await self.conversation_store.shrink_context(thread_id)

            logger.info(f"Summary created for thread: {thread_id}")
            return True

        except Exception as e:
            logger.error(f"Summarization failed for thread {thread_id}: {e}")
            return False

    async def retrieve_context(
        self,
        tenant_id: str,
        thread_id: UUID,
        query_text: Optional[str] = None,
        es_limit: Optional[int] = 5
    ) -> tuple[MessageParams, list[dict]]:
        """
        检索完整的对话上下文（短期记忆 + 长期记忆）

        Args:
            tenant_id: 租户标识
            thread_id: 对话线程ID
            query_text: 可选的查询文本，用于搜索相关长期记忆
            es_limit: Elasticsearch搜索结果限制数量

        Returns:
            tuple: (短期消息列表, 长期摘要列表)
        """
        try:
            # 获取短期记忆
            short_term_messages = await self.conversation_store.get_recent(thread_id)

            # 获取长期记忆
            if query_text:
                long_term_summaries = await self.elasticsearch_index.search(
                    tenant_id=tenant_id,
                    query_text=query_text,
                    thread_id=thread_id,
                    limit=es_limit
                )
            else:
                long_term_summaries = await self.elasticsearch_index.get_thread_summaries(
                    tenant_id=tenant_id,
                    thread_id=thread_id,
                    limit=es_limit
                )

            return short_term_messages, long_term_summaries

        except Exception as e:
            logger.error(f"Failed to retrieve context for thread {thread_id}: {e}")
            short_term_messages: MessageParams = []
            long_term_summaries: list[dict] = []
            return short_term_messages, long_term_summaries

    async def cleanup_expired_memories(self):
        """清理过期的记忆条目"""
        try:
            await self.elasticsearch_index.delete_expired()
            logger.info("Expired memories cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
