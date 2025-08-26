"""
对话工作区模块

该模块提供基于领域的对话管理功能，包括线程创建、生命周期管理和消息处理。
"""

from .thread import router as conversations

__all__ = [
    "conversations"
]