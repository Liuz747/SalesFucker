"""
语音处理模块

该包提供语音识别和转录功能，支持中文和英文语音处理。
基于OpenAI Whisper实现高质量的语音转文本服务。

核心功能:
- 多语言语音识别（中文/英文）
- 音频预处理和优化
- 实时转录和批量处理
- 置信度评估和质量控制
"""

from .whisper_service import WhisperService
from .audio_processor import AudioProcessor
from .voice_analyzer import VoiceAnalyzer

__all__ = [
    "WhisperService",
    "AudioProcessor", 
    "VoiceAnalyzer"
]