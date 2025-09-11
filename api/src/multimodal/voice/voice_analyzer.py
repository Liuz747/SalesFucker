"""
语音分析器

该模块提供完整的语音分析服务，集成音频预处理和语音识别功能。
为多智能体系统提供高质量的语音转文本服务。

核心功能:
- 完整的语音处理流水线
- 智能语言检测和处理
- 质量评估和置信度计算
- 缓存和性能优化
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import json

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    MultiModalConstants
)
from .whisper_service import WhisperService
from .audio_processor import AudioProcessor


class VoiceAnalyzer(LoggerMixin):
    """
    语音分析器类
    
    集成音频预处理和语音识别，提供完整的语音分析服务。
    支持多语言处理、质量优化和智能缓存。
    
    属性:
        whisper_service: Whisper识别服务
        audio_processor: 音频预处理器
        cache: 结果缓存字典
        tenant_id: 租户标识符
    """
    
    def __init__(self, tenant_id: str, openai_api_key: str, temp_dir: Optional[str] = None):
        """
        初始化语音分析器
        
        Args:
            tenant_id: 租户标识符
            openai_api_key: OpenAI API密钥
            temp_dir: 临时文件目录
        """
        super().__init__()
        self.tenant_id = tenant_id
        self.whisper_service = WhisperService(openai_api_key)
        self.audio_processor = AudioProcessor(temp_dir)
        self.cache = {}  # 简单内存缓存，生产环境应使用Redis
        
        self.logger.info(f"语音分析器已初始化 - 租户: {tenant_id}")
    
    async def analyze_voice(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        enhance_audio: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        分析语音文件
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言（zh/en），None为自动检测
            enhance_audio: 是否进行音频增强
            use_cache: 是否使用缓存
            
        Returns:
            完整的语音分析结果
        """
        start_time = datetime.now()
        self.logger.info(f"开始语音分析: {audio_path}, 语言: {language}")
        
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(audio_path, language, enhance_audio)
            
            # 检查缓存
            if use_cache and cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if self._is_cache_valid(cached_result):
                    self.logger.info(f"使用缓存结果: {audio_path}")
                    return cached_result
            
            # 步骤1: 验证和预处理音频
            validation_result = await self.audio_processor.validate_audio_file(audio_path)
            if not validation_result['is_valid']:
                raise ValueError(f"音频文件无效: {validation_result['error']}")
            
            processed_path = audio_path
            processing_info = validation_result
            
            # 步骤2: 音频预处理（如需要）
            if enhance_audio:
                processing_result = await self.audio_processor.process_audio_file(audio_path)
                processed_path = processing_result['output_path']
                processing_info = processing_result['processed_info']
            
            # 步骤3: 语音识别
            transcription_result = await self.whisper_service.transcribe_audio(
                processed_path, 
                language=language,
                prompt=self._generate_prompt(language)
            )
            
            # 步骤4: 结果整合和分析
            analysis_result = self._create_analysis_result(
                audio_path,
                processing_info,
                transcription_result,
                language,
                enhance_audio
            )
            
            # 步骤5: 质量评估
            analysis_result = self._evaluate_quality(analysis_result)
            
            # 步骤6: 缓存结果
            if use_cache:
                analysis_result['cached_at'] = get_current_datetime()
                self.cache[cache_key] = analysis_result
            
            processing_time = get_processing_time_ms(start_time)
            analysis_result['total_processing_time_ms'] = processing_time
            
            self.logger.info(
                f"语音分析完成: {audio_path}, "
                f"总耗时: {processing_time}ms, "
                f"文本: {analysis_result.get('text', '')[:50]}..., "
                f"置信度: {analysis_result.get('confidence', 0):.2f}"
            )
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"语音分析失败: {audio_path}, 错误: {e}")
            raise
    
    def _generate_cache_key(self, audio_path: str, language: Optional[str], enhance_audio: bool) -> str:
        """
        生成缓存键
        
        Args:
            audio_path: 音频文件路径
            language: 语言
            enhance_audio: 是否增强
            
        Returns:
            缓存键字符串
        """
        # 使用文件路径、修改时间、参数生成唯一键
        try:
            from pathlib import Path
            file_stat = Path(audio_path).stat()
            key_data = {
                'path': audio_path,
                'mtime': file_stat.st_mtime,
                'size': file_stat.st_size,
                'language': language,
                'enhance': enhance_audio,
                'tenant': self.tenant_id
            }
            
            key_string = json.dumps(key_data, sort_keys=True)
            return hashlib.md5(key_string.encode()).hexdigest()
            
        except Exception:
            # 降级到简单键
            return hashlib.md5(f"{audio_path}_{language}_{enhance_audio}_{self.tenant_id}".encode()).hexdigest()
    
    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cached_result: 缓存的结果
            
        Returns:
            是否有效
        """
        if 'cached_at' not in cached_result:
            return False
        
        cached_time = cached_result['cached_at']
        current_time = get_current_datetime()
        
        # 检查缓存时间
        cache_age = (current_time - cached_time).total_seconds()
        return cache_age < MultiModalConstants.VOICE_CACHE_TTL
    
    def _generate_prompt(self, language: Optional[str]) -> Optional[str]:
        """
        生成Whisper提示文本
        
        Args:
            language: 语言代码
            
        Returns:
            提示文本
        """
        if language == 'zh':
            return "这是关于化妆品和美容护肤的对话。可能包含产品名称、护肤问题、化妆技巧等内容。"
        elif language == 'en':
            return "This is a conversation about cosmetics and beauty skincare. May include product names, skincare concerns, makeup techniques."
        
        return None
    
    def _create_analysis_result(
        self,
        original_path: str,
        processing_info: Dict[str, Any],
        transcription_result: Dict[str, Any],
        requested_language: Optional[str],
        enhanced: bool
    ) -> Dict[str, Any]:
        """
        创建分析结果
        
        Args:
            original_path: 原始文件路径
            processing_info: 处理信息
            transcription_result: 转录结果
            requested_language: 请求的语言
            enhanced: 是否增强处理
            
        Returns:
            完整分析结果
        """
        return {
            # 基本信息
            'tenant_id': self.tenant_id,
            'original_path': original_path,
            'requested_language': requested_language,
            'enhanced': enhanced,
            
            # 转录结果
            'text': transcription_result.get('text', ''),
            'language': transcription_result.get('language', ''),
            'confidence': transcription_result.get('confidence', 0.0),
            
            # 音频信息
            'duration': processing_info.get('duration') or transcription_result.get('duration'),
            'sample_rate': processing_info.get('sample_rate'),
            'channels': processing_info.get('channels'),
            'file_size': processing_info.get('file_size'),
            
            # 质量指标
            'is_high_quality': transcription_result.get('is_high_quality', False),
            'language_match': transcription_result.get('language_match', False),
            'detected_language': transcription_result.get('detected_language'),
            
            # 详细信息
            'segments': transcription_result.get('segments', []),
            'processing_details': {
                'audio_processing_time': processing_info.get('processing_time_ms'),
                'transcription_time': transcription_result.get('processing_time_ms'),
                'enhanced': enhanced
            },
            
            # 时间戳
            'analyzed_at': get_current_datetime()
        }
    
    def _evaluate_quality(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估分析质量
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            添加质量评估的结果
        """
        quality_score = 0.0
        quality_factors = []
        
        # 置信度因子
        confidence = analysis_result.get('confidence', 0)
        quality_factors.append(('confidence', confidence, 0.4))
        
        # 语言匹配因子
        language_match = analysis_result.get('language_match', False)
        language_score = 1.0 if language_match else 0.7
        quality_factors.append(('language_match', language_score, 0.2))
        
        # 文本长度因子
        text_length = len(analysis_result.get('text', ''))
        length_score = min(1.0, text_length / 20) if text_length > 0 else 0.1
        quality_factors.append(('text_length', length_score, 0.2))
        
        # 音频时长因子
        duration = analysis_result.get('duration')
        if duration:
            if MultiModalConstants.MIN_AUDIO_DURATION <= duration <= MultiModalConstants.MAX_AUDIO_DURATION:
                duration_score = 1.0
            else:
                duration_score = 0.7
        else:
            duration_score = 0.5
        quality_factors.append(('duration', duration_score, 0.2))
        
        # 计算加权质量分数
        total_weight = 0
        for factor_name, score, weight in quality_factors:
            quality_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            quality_score = quality_score / total_weight
        
        # 添加质量信息
        analysis_result.update({
            'quality_score': round(quality_score, 3),
            'quality_factors': {
                name: {'score': score, 'weight': weight}
                for name, score, weight in quality_factors
            },
            'is_reliable': quality_score >= 0.7,
            'quality_level': self._get_quality_level(quality_score)
        })
        
        return analysis_result
    
    def _get_quality_level(self, quality_score: float) -> str:
        """
        获取质量等级
        
        Args:
            quality_score: 质量分数
            
        Returns:
            质量等级字符串
        """
        if quality_score >= 0.9:
            return 'excellent'
        elif quality_score >= 0.7:
            return 'good'
        elif quality_score >= 0.5:
            return 'fair'
        else:
            return 'poor'
    
    async def batch_analyze_voices(
        self, 
        audio_paths: List[str], 
        language: Optional[str] = None,
        enhance_audio: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量分析语音文件
        
        Args:
            audio_paths: 音频文件路径列表
            language: 指定语言
            enhance_audio: 是否音频增强
            
        Returns:
            分析结果列表
        """
        self.logger.info(f"开始批量语音分析，文件数量: {len(audio_paths)}")
        
        # 创建异步任务
        tasks = [
            self.analyze_voice(path, language, enhance_audio) 
            for path in audio_paths
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"批量分析失败 {audio_paths[i]}: {result}")
            else:
                successful_results.append(result)
        
        self.logger.info(f"批量语音分析完成，成功: {len(successful_results)}/{len(audio_paths)}")
        return successful_results
    
    async def clear_cache(self, max_age_hours: int = 24):
        """
        清理过期缓存
        
        Args:
            max_age_hours: 最大缓存时间（小时）
        """
        current_time = get_current_datetime()
        keys_to_remove = []
        
        for key, cached_result in self.cache.items():
            if 'cached_at' in cached_result:
                cache_age = (current_time - cached_result['cached_at']).total_seconds()
                if cache_age > max_age_hours * 3600:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        if keys_to_remove:
            self.logger.info(f"清理过期缓存，删除: {len(keys_to_remove)} 条记录")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            服务状态信息
        """
        whisper_health = await self.whisper_service.health_check()
        audio_stats = self.audio_processor.get_processing_stats()
        
        return {
            'status': 'healthy' if whisper_health['status'] == 'healthy' else 'degraded',
            'tenant_id': self.tenant_id,
            'cache_size': len(self.cache),
            'whisper_service': whisper_health,
            'audio_processor': audio_stats,
            'timestamp': get_current_datetime()
        }