"""
Conversation Memory Configuration

Manages Redis-based short-term conversation storage settings.
"""

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class ConversationConfig(BaseSettings):
    """短期对话记忆配置"""

    # TTL Configuration
    CONVERSATION_TTL_DAYS: PositiveInt = Field(
        description="Redis对话过期时间（天）",
        default=7,
    )

    PRESERVATION_TRIGGER_OFFSET_MINUTES: PositiveInt = Field(
        description="在过期前多少分钟触发保存检查",
        default=45,
    )

    # Heuristics Configuration
    MIN_MESSAGES_TO_PRESERVE: PositiveInt = Field(
        description="保存对话的最小消息数",
        default=3,
    )

    @property
    def conversation_ttl_seconds(self) -> int:
        """计算Redis TTL（秒）"""
        return self.CONVERSATION_TTL_DAYS * 24 * 60 * 60

    @property
    def preservation_wait_seconds(self) -> int:
        """计算工作流等待时间（秒）"""
        wait_time = self.conversation_ttl_seconds - (self.PRESERVATION_TRIGGER_OFFSET_MINUTES * 60)
        if wait_time < 0:
            raise ValueError(
                f"PRESERVATION_TRIGGER_OFFSET_MINUTES ({self.PRESERVATION_TRIGGER_OFFSET_MINUTES}) "
                f"must be less than CONVERSATION_TTL_DAYS ({self.CONVERSATION_TTL_DAYS} days)"
            )
        return wait_time
