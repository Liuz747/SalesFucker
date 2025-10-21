"""
短期会话记忆工具。

该模块提供轻量级的进程内环形缓冲，用于按 thread 维度维护最近
若干条消息，满足多轮对话的短期记忆需求。
"""

from uuid import UUID

import msgpack
from redis.asyncio import Redis

from infra.cache import get_redis_client
from infra.runtimes import CompletionsRequest
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
        self.redis_client: Redis | None = None

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
        packed: list[bytes],
    ):
        redis_client = self.redis_client or await get_redis_client()
        key = self._key(thread_id)

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
    async def get_recent(self,  thread_id: UUID, limit: int | None = None) -> MessageParams:
        """获取最近 limit 条消息（默认使用 store 的 max_messages）。"""
        redis = self.redis_client or await get_redis_client()
        key = self._key(thread_id)
        n = limit or self.max_messages
        # last n: [-n, -1]
        raw_items = await redis.lrange(key, -n, -1)
        return [self._unpack_message(b) for b in raw_items]

    # ------------- request builder -------------
    async def prepare_request(
        self,
        *,
        run_id: UUID,
        provider: str,
        model: str,
        messages: MessageParams,
        thread_id: UUID,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> CompletionsRequest:
        """
        1) 将本次输入写入会话短期记忆
        2) 读取最近 N 条构建 LLMRequest
        """
        filtered = []
        system = []

        for message in messages:
            if message.role == "system":
                system.append(message)
            else:
                filtered.append(self._pack_message(message))
        
        # append user message then read the window
        await self.append_messages(thread_id, filtered)

        recent = await self.get_recent(thread_id, self.max_messages)
        window = system + recent if system else recent

        return CompletionsRequest(
            id=run_id,
            model=model,
            provider=provider,
            messages=window,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            thread_id=thread_id,
        )

    async def save_assistant_reply(self, thread_id: UUID | str, content: str) -> None:
        """生成后将助手消息写回上下文。"""
        packed = [self._pack_message(Message(role="assistant", content=content))]
        await self.append_messages(thread_id, packed)