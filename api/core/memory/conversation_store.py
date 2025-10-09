"""
短期会话记忆工具。

该模块提供轻量级的进程内环形缓冲，用于按 (tenant, thread) 维度维护最近
若干条消息，满足多轮对话的短期记忆需求。
"""

from uuid import UUID
from collections.abc import Iterable

import msgpack
from redis.asyncio import Redis

from infra.cache import get_redis_client
from infra.runtimes import LLMRequest, Message
from utils import get_component_logger


logger = get_component_logger(__name__)


class ConversationStore:
    """
    短期会话存储（Redis 列表 + Pipeline + msgpack）
    每条消息作为一个 list 元素存储，使用 LTRIM 限制长度，并设置 TTL。
    """

    def __init__(self):
        self.max_messages = 20
        self.redis_client: Redis | None = None

    # ------------- key helpers -------------
    @staticmethod
    def _key(tenant_id: str, thread_id: UUID) -> str:
        return f"conversation:{tenant_id}:{str(thread_id)}"

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
        tenant_id: str,
        thread_id: UUID,
        messages: Iterable[Message]
    ):
        redis_client = self.redis_client or await get_redis_client()
        key = f"conversation:{tenant_id}:{str(thread_id)}"

        packed = [self._pack_message(m) for m in messages]

        async with redis_client.pipeline(transaction=True) as pipe:
            await pipe.rpush(key, *packed)
            await pipe.ltrim(key, -self.max_messages, -1)
            await pipe.expire(key, 3600)
            result = await pipe.execute()

        # result[0] is RPUSH length, result[1] is OK for LTRIM, result[2] is expire(True/False)
        new_len = int(result[0]) if result and isinstance(result[0], (int,)) else 0
        logger.debug(f"append {len(packed)} -> {key}, len={new_len}")
        return new_len

    # ------------- read path -------------
    async def get_recent(self, tenant_id: str, thread_id: UUID, limit: int | None = None) -> Iterable[Message]:
        """获取最近 limit 条消息（默认使用 store 的 max_messages）。"""
        redis = self.redis_client or await get_redis_client()
        key = self._key(tenant_id, thread_id)
        n = limit or self.max_messages
        # last n: [-n, -1]
        raw_items = await redis.lrange(key, -n, -1)
        return [self._unpack_message(b) for b in raw_items]

    # ------------- request builder -------------
    async def prepare_request(
        self,
        *,
        provider_id: str,
        model: str,
        message: Iterable[Message],
        tenant_id: str,
        thread_id: UUID,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMRequest:
        """
        1) 将本次输入写入会话短期记忆
        2) 读取最近 N 条构建 LLMRequest
        """
        # append user message then read the window
        await self.append_messages(tenant_id, thread_id, message)
        window = await self.get_recent(tenant_id, thread_id, self.max_messages)

        return LLMRequest(
            model=model,
            provider=provider_id,  # your client expects request.id to match an active provider; provider is informational
            messages=window,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tenant_id=tenant_id,
            thread_id=thread_id,
        )

    async def save_assistant_reply(self, tenant_id: str, thread_id: UUID | str, content: str) -> None:
        """生成后将助手消息写回上下文。"""
        await self.append_messages(tenant_id, thread_id, [Message(role="assistant", content=content)])