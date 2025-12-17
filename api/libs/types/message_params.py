from collections.abc import Sequence
from enum import StrEnum
from typing import Literal, TypeAlias, Any

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


class ToolCall(BaseModel):
    """
    工具调用信息

    当 LLM 决定调用工具时，assistant 消息会包含这些信息
    """
    id: str
    type: Literal["function"] = "function"
    function: dict[str, Any]  # {"name": str, "arguments": str}


class AssistantMessage(BaseModel):
    """
    助手消息（支持工具调用）

    可以包含：
    - 纯文本回复
    - 工具调用请求
    - 两者都有
    """
    role: Literal["assistant"]
    content: InputContentParams | None = None
    tool_calls: list[ToolCall] | None = None


class ToolMessage(BaseModel):
    """
    工具执行结果消息

    用于将工具执行结果返回给 LLM
    """
    role: Literal["tool"]
    content: str  # 工具执行结果（通常是 JSON 字符串）
    tool_call_id: str  # 关联到哪个工具调用


class UserMessage(BaseModel):
    """用户消息"""
    role: Literal["user"]
    content: InputContentParams


class SystemMessage(BaseModel):
    """系统提示消息"""
    role: Literal["system"]
    content: InputContentParams


# 消息参数类型
MessageParams: TypeAlias = Sequence[UserMessage | AssistantMessage | SystemMessage | ToolMessage | Message]
