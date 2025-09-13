"""
多模态处理模块

该包提供多智能体系统的多模态处理能力，包括语音识别和图像分析。

核心功能:
- 语音转文本处理
- 图像内容分析  
- 多模态消息处理
- 异步处理和缓存
- 多租户支持

模块组织:
- core: 核心多模态消息和处理框架
- voice: 语音处理和转录服务
- image: 图像分析和识别服务
- storage: 多模态数据存储管理
"""

from .core.attachment import BaseAttachment, AudioAttachment, ImageAttachment
from .core.message import MultiModalMessage, ProcessingResult
from .core.processor import MultiModalProcessor

__all__ = [
    "BaseAttachment",
    "AudioAttachment", 
    "ImageAttachment",
    "MultiModalMessage",
    "ProcessingResult",
    "MultiModalProcessor"
]