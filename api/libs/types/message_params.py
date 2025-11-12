from collections.abc import Iterable
from enum import StrEnum
from typing import TypeAlias

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
    role: str
    content: InputContentParams


MessageParams: TypeAlias = Iterable[Message]