from collections.abc import Sequence
from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel

from .content_params import InputContentParams


class MessageType(StrEnum):
    """消息类型枚举"""
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    TRIGGER = "trigger"
    SUGGESTION = "suggestion"


class Message(BaseModel):
    """消息模型"""
    role: Literal["user", "assistant", "system"]
    content: InputContentParams


MessageParams: TypeAlias = Sequence[Message]
