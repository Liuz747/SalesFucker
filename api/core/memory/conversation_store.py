"""
短期会话记忆工具。

该模块提供轻量级的进程内环形缓冲，用于按 thread 维度维护最近
若干条消息，满足多轮对话的短期记忆需求。
"""

from uuid import UUID

import msgpack

from libs.factory import infra_registry
from libs.types import Message, MessageParams
from utils import get_component_logger


logger = get_component_logger(__name__)


class ConversationStore:
    """
    短期会话存储（Redis 列表 + Pipeline + msgpack）
    每条消息作为一个 list 元素存储，使用 LTRIM 限制长度，并设置 TTL。
    """

    def __init__(self):
        self.max_messages = 20
        self.redis_client = infra_registry.get_cached_clients().redis

    # ------------- key helpers -------------
    @staticmethod
    def _key(thread_id: UUID) -> str:
        return f"conversation:{str(thread_id)}"

    # ------------- serialization -------------
    @staticmethod
    def _pack_message(msg: Message):
        return msgpack.packb(msg.model_dump(), use_bin_type=True)

    @staticmethod
    def _unpack_message(payload) -> Message:
        data = msgpack.unpackb(payload, raw=False)
        return Message(**data)

    # ------------- write path -------------
    async def append_messages(
        self,
        thread_id: UUID,
        messages: list[Message],
    ):
        key = self._key(thread_id)

        if not messages:
            logger.debug(f"append_messages 跳过空消息写入 -> {key}")
            return await self.redis_client.llen(key)

        packed = [self._pack_message(msg) for msg in messages]

        async with self.redis_client.pipeline(transaction=True) as pipe:
            await pipe.rpush(key, *packed)
            await pipe.ltrim(key, -self.max_messages, -1)
            await pipe.expire(key, 3600)
            result = await pipe.execute()

        # result[0] 是 RPUSH 长度, result[1] 是 LTRIM 返回值, result[2] 是 expire(True/False)
        new_len = int(result[0])
        logger.debug(f"append {len(messages)} -> {key}, len={new_len}")
        return new_len

    # ------------- read path -------------
    async def get_recent(self,  thread_id: UUID, limit: int | None = None) -> MessageParams:
        """获取最近 limit 条消息（默认使用 store 的 max_messages）。"""
        key = self._key(thread_id)
        message_limit = limit or self.max_messages
        # last message_limit: [-message_limit, -1]
        raw_items = await self.redis_client.lrange(key, -message_limit, -1)
        return [self._unpack_message(b) for b in raw_items]

    # ---------------- Clear / Shrink ----------------
    async def shrink_context(self, thread_id: UUID, keep_last: int = 5):
        key = self._key(thread_id)
        await self.redis_client.ltrim(key, -keep_last, -1)
        logger.debug(f"[ConversationStore] shrink -> {keep_last}")
