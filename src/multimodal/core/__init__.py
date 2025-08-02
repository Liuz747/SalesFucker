"""
多模态核心处理模块

提供多模态消息处理的核心功能和基础架构。
"""

from .attachment import BaseAttachment, AudioAttachment, ImageAttachment  
from .message import MultiModalMessage, ProcessingResult
from .processor import MultiModalProcessor

__all__ = [
    "BaseAttachment",
    "AudioAttachment",
    "ImageAttachment", 
    "MultiModalMessage",
    "ProcessingResult",
    "MultiModalProcessor"
]