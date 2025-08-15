"""
Whisper语音识别服务

该模块提供基于OpenAI Whisper的语音识别服务。
支持中文和英文语音的高质量转录，包含置信度评估和错误处理。

核心功能:
- Whisper API集成和调用
- 多语言支持（中文/英文）
- 异步处理和超时控制
- 置信度评估和质量保证
"""

import asyncio
import aiofiles
from typing import Dict, Any, Optional, List
from datetime import datetime
import openai
from pathlib import Path

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    with_error_handling,
    MultiModalConstants
)


class WhisperService(LoggerMixin):
    """
    Whisper语音识别服务类
    
    提供基于OpenAI Whisper的语音转文本服务。
    支持异步处理、多语言识别和质量控制。
    
    属性:
        client: OpenAI客户端
        supported_languages: 支持的语言列表
        default_language: 默认语言
        timeout: 处理超时时间
    """
    
    def __init__(self, api_key: str):
        """
        初始化Whisper服务
        
        Args:
            api_key: OpenAI API密钥
        """
        super().__init__()
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.supported_languages = MultiModalConstants.SUPPORTED_LANGUAGES
        self.default_language = MultiModalConstants.DEFAULT_VOICE_LANGUAGE
        self.timeout = MultiModalConstants.VOICE_PROCESSING_TIMEOUT / 1000  # 转换为秒
        
        self.logger.info("Whisper语音识别服务已初始化")
    
    @with_error_handling()
    async def transcribe_audio(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言（zh/en），None为自动检测
            prompt: 提示文本，用于提高准确性
            
        Returns:
            转录结果字典，包含文本、语言、置信度等信息
        """
        start_time = datetime.now()
        self.logger.info(f"开始转录音频: {audio_path}, 语言: {language}")
        
        try:
            # 验证文件存在
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
            # 验证语言参数
            if language and language not in self.supported_languages:
                self.logger.warning(f"不支持的语言: {language}，使用默认语言: {self.default_language}")
                language = self.default_language
            
            # 调用Whisper API
            async with aiofiles.open(audio_path, 'rb') as audio_file:
                audio_data = await audio_file.read()
                
                # 创建转录请求
                transcription = await asyncio.wait_for(
                    self._call_whisper_api(audio_data, audio_path, language, prompt),
                    timeout=self.timeout
                )
            
            # 处理转录结果
            result = self._process_transcription_result(transcription, language)
            
            processing_time = get_processing_time_ms(start_time)
            result['processing_time_ms'] = processing_time
            
            self.logger.info(
                f"音频转录完成: {audio_path}, "
                f"耗时: {processing_time}ms, "
                f"文本长度: {len(result.get('text', ''))}, "
                f"置信度: {result.get('confidence', 0):.2f}"
            )
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"音频转录超时: {audio_path}")
            raise Exception(f"语音转录超时（{self.timeout}秒）")
        except Exception as e:
            self.logger.error(f"音频转录失败: {audio_path}, 错误: {e}")
            raise
    
    async def _call_whisper_api(
        self, 
        audio_data: bytes, 
        filename: str,
        language: Optional[str], 
        prompt: Optional[str]
    ) -> Any:
        """
        调用Whisper API
        
        Args:
            audio_data: 音频数据
            filename: 文件名
            language: 语言代码
            prompt: 提示文本
            
        Returns:
            Whisper API响应
        """
        # 构造API参数
        kwargs = {
            'model': 'whisper-1',
            'response_format': 'verbose_json',  # 获取详细信息包括置信度
            'temperature': 0.0  # 降低随机性提高准确性
        }
        
        if language:
            kwargs['language'] = language
        
        if prompt:
            kwargs['prompt'] = prompt
        
        # 调用API
        transcription = await self.client.audio.transcriptions.create(
            file=(filename, audio_data, 'audio/mpeg'),
            **kwargs
        )
        
        return transcription
    
    def _process_transcription_result(self, transcription: Any, requested_language: Optional[str]) -> Dict[str, Any]:
        """
        处理转录结果
        
        Args:
            transcription: Whisper API响应
            requested_language: 请求的语言
            
        Returns:
            处理后的结果字典
        """
        # 提取基本信息
        text = transcription.text.strip()
        detected_language = getattr(transcription, 'language', None)
        
        # 计算置信度（基于多个因素）
        confidence = self._calculate_confidence(transcription, text, detected_language, requested_language)
        
        # 检测实际语言
        actual_language = self._detect_language(text, detected_language)
        
        result = {
            'text': text,
            'language': actual_language,
            'detected_language': detected_language,
            'requested_language': requested_language,
            'confidence': confidence,
            'duration': getattr(transcription, 'duration', None),
            'segments': self._extract_segments(transcription)
        }
        
        # 添加质量标记
        result['is_high_quality'] = confidence >= MultiModalConstants.MIN_VOICE_CONFIDENCE
        result['language_match'] = (
            not requested_language or 
            actual_language == requested_language or
            actual_language.startswith(requested_language) or
            requested_language.startswith(actual_language)
        )
        
        return result
    
    def _calculate_confidence(
        self, 
        transcription: Any, 
        text: str, 
        detected_language: Optional[str],
        requested_language: Optional[str]
    ) -> float:
        """
        计算转录置信度
        
        Args:
            transcription: Whisper响应
            text: 转录文本
            detected_language: 检测到的语言
            requested_language: 请求的语言
            
        Returns:
            置信度分数（0-1）
        """
        confidence_factors = []
        
        # 基础置信度（来自API）
        if hasattr(transcription, 'segments') and transcription.segments:
            segment_scores = [
                segment.avg_logprob for segment in transcription.segments 
                if hasattr(segment, 'avg_logprob')
            ]
            if segment_scores:
                # 将logprob转换为0-1范围的置信度
                avg_logprob = sum(segment_scores) / len(segment_scores)
                base_confidence = max(0, min(1, (avg_logprob + 1) / 1))  # 简化映射
                confidence_factors.append(base_confidence)
        
        # 文本长度因子
        if len(text) > 5:  # 有意义的文本长度
            length_factor = min(1.0, len(text) / 20)  # 20字符达到满分
            confidence_factors.append(length_factor)
        else:
            confidence_factors.append(0.3)  # 文本太短降低置信度
        
        # 语言匹配因子
        if requested_language and detected_language:
            if detected_language.startswith(requested_language):
                confidence_factors.append(1.0)
            else:
                confidence_factors.append(0.7)  # 语言不匹配降低置信度
        else:
            confidence_factors.append(0.8)  # 无语言信息时中等置信度
        
        # 中文特殊处理
        if self._contains_chinese(text):
            if requested_language == 'zh' or detected_language == 'zh':
                confidence_factors.append(0.9)  # 中文匹配
            else:
                confidence_factors.append(0.6)  # 检测到中文但未指定中文
        
        # 计算最终置信度（加权平均）
        if confidence_factors:
            final_confidence = sum(confidence_factors) / len(confidence_factors)
        else:
            final_confidence = 0.5  # 默认中等置信度
        
        return round(final_confidence, 3)
    
    def _detect_language(self, text: str, detected_language: Optional[str]) -> str:
        """
        检测文本语言
        
        Args:
            text: 转录文本
            detected_language: API检测的语言
            
        Returns:
            语言代码
        """
        # 优先使用API检测结果
        if detected_language and detected_language in self.supported_languages:
            return detected_language
        
        # 基于文本内容检测
        if self._contains_chinese(text):
            return 'zh'
        elif self._contains_english(text):
            return 'en'
        
        # 默认返回检测语言或默认语言
        return detected_language or self.default_language
    
    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    
    def _contains_english(self, text: str) -> bool:
        """检查文本是否包含英文"""
        return any('a' <= char.lower() <= 'z' for char in text)
    
    def _extract_segments(self, transcription: Any) -> List[Dict[str, Any]]:
        """
        提取转录片段信息
        
        Args:
            transcription: Whisper响应
            
        Returns:
            片段信息列表
        """
        segments = []
        
        if hasattr(transcription, 'segments') and transcription.segments:
            for segment in transcription.segments:
                segment_info = {
                    'start': getattr(segment, 'start', 0),
                    'end': getattr(segment, 'end', 0),
                    'text': getattr(segment, 'text', '').strip()
                }
                
                # 添加置信度信息（如果可用）
                if hasattr(segment, 'avg_logprob'):
                    segment_info['avg_logprob'] = segment.avg_logprob
                if hasattr(segment, 'no_speech_prob'):
                    segment_info['no_speech_prob'] = segment.no_speech_prob
                
                segments.append(segment_info)
        
        return segments
    
    @with_error_handling()
    async def batch_transcribe(self, audio_paths: List[str], language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量转录音频文件
        
        Args:
            audio_paths: 音频文件路径列表
            language: 指定语言
            
        Returns:
            转录结果列表
        """
        self.logger.info(f"开始批量转录，文件数量: {len(audio_paths)}")
        
        # 创建异步任务
        tasks = [
            self.transcribe_audio(path, language) 
            for path in audio_paths
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"批量转录失败 {audio_paths[i]}: {result}")
            else:
                successful_results.append(result)
        
        self.logger.info(f"批量转录完成，成功: {len(successful_results)}/{len(audio_paths)}")
        return successful_results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            服务状态信息
        """
        try:
            # 简单的API测试（可选实现）
            return {
                'status': 'healthy',
                'service': 'whisper',
                'supported_languages': self.supported_languages,
                'default_language': self.default_language,
                'timeout': self.timeout,
                'timestamp': get_current_datetime()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': get_current_datetime()
            }