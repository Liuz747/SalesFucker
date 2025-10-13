from collections.abc import Iterable
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel

from ..constants import MessageConstants
from .content_params import InputContentParams


class MessageType(StrEnum):
    """消息类型枚举"""
    QUERY = MessageConstants.QUERY
    RESPONSE = MessageConstants.RESPONSE
    NOTIFICATION = MessageConstants.NOTIFICATION
    TRIGGER = MessageConstants.TRIGGER
    SUGGESTION = MessageConstants.SUGGESTION


class Message(BaseModel):
    role: str
    content: InputContentParams


MessageParams: TypeAlias = Iterable[Message]