"""
缓存集成模块

该模块提供缓存增强的多模态服务包装器。
透明地为语音和图像处理服务添加缓存支持。

核心功能:
- 服务缓存装饰器
- 智能缓存策略
- 缓存性能监控
- 降级机制支持
"""

import asyncio
import functools
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime
import hashlib
import aiofiles

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler
)
from .multimodal_cache import MultiModalCache


class CachedMultiModalService(LoggerMixin):
    """
    缓存增强的多模态服务基类
    
    为多模态处理服务提供透明的缓存支持。
    
    属性:
        cache: 缓存管理器
        service_name: 服务名称
        cache_enabled: 缓存是否启用
    """
    
    def __init__(
        self,
        cache: MultiModalCache,
        service_name: str,
        cache_enabled: bool = True
    ):
        """
        初始化缓存增强服务
        
        Args:
            cache: 缓存管理器
            service_name: 服务名称
            cache_enabled: 是否启用缓存
        """
        super().__init__()
        self.cache = cache
        self.service_name = service_name
        self.cache_enabled = cache_enabled
        
        # 性能统计
        self.performance_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_requests': 0,
            'cache_save_time_ms': 0,
            'processing_time_saved_ms': 0
        }
        
        self.logger.info(f"缓存增强服务已初始化: {service_name}")


class CachedWhisperService(CachedMultiModalService):
    """缓存增强的Whisper服务"""
    
    def __init__(self, whisper_service, cache: MultiModalCache):
        super().__init__(cache, "whisper_service")
        self.whisper_service = whisper_service
    
    @with_error_handling()
    async def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        缓存增强的音频转录
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言
            prompt: 提示文本
            
        Returns:
            转录结果
        """
        start_time = datetime.now()
        self.performance_stats['total_requests'] += 1
        
        try:
            # 读取音频文件内容用于缓存键生成
            async with aiofiles.open(audio_path, 'rb') as f:
                audio_content = await f.read()
            
            # 检查缓存
            if self.cache_enabled:
                cache_key_data = {
                    'audio_hash': hashlib.sha256(audio_content).hexdigest(),
                    'language': language,
                    'prompt': prompt
                }
                
                cached_result = await self.cache.get_voice_transcription(
                    audio_content, language or 'auto'
                )
                
                if cached_result:
                    self.performance_stats['cache_hits'] += 1
                    
                    # 添加缓存指示器
                    cached_result['from_cache'] = True
                    cached_result['cache_hit_time'] = get_current_datetime()
                    
                    cache_time = get_processing_time_ms(start_time)
                    self.performance_stats['cache_save_time_ms'] += cache_time
                    
                    self.logger.debug(f"语音转录缓存命中，节省处理时间: {cache_time}ms")
                    return cached_result
            
            # 缓存未命中，调用原始服务
            self.performance_stats['cache_misses'] += 1
            result = await self.whisper_service.transcribe_audio(
                audio_path, language, prompt
            )
            
            # 保存到缓存
            if self.cache_enabled and result.get('confidence', 0) > 0.5:
                await self.cache.cache_voice_transcription(
                    audio_content,
                    language or result.get('language', 'auto'),
                    result
                )
            
            result['from_cache'] = False
            processing_time = get_processing_time_ms(start_time)
            
            self.logger.debug(f"语音转录完成，处理时间: {processing_time}ms")
            return result
            
        except Exception as e:
            self.logger.error(f"缓存增强的语音转录失败: {e}")
            raise
    
    async def batch_transcribe(
        self,
        audio_paths: list,
        language: Optional[str] = None
    ) -> list:
        """批量转录（支持缓存）"""
        tasks = [
            self.transcribe_audio(path, language)
            for path in audio_paths
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)


class CachedGPT4VService(CachedMultiModalService):
    """缓存增强的GPT-4V服务"""
    
    def __init__(self, gpt4v_service, cache: MultiModalCache):
        super().__init__(cache, "gpt4v_service")
        self.gpt4v_service = gpt4v_service
    
    @with_error_handling()
    async def analyze_skin(
        self,
        image_path: str,
        language: str = 'zh'
    ) -> Dict[str, Any]:
        """
        缓存增强的皮肤分析
        
        Args:
            image_path: 图像文件路径
            language: 输出语言
            
        Returns:
            皮肤分析结果
        """
        return await self._cached_analyze(
            self.gpt4v_service.analyze_skin,
            image_path,
            'skin_analysis',
            language
        )
    
    @with_error_handling()
    async def recognize_product(
        self,
        image_path: str,
        language: str = 'zh'
    ) -> Dict[str, Any]:
        """
        缓存增强的产品识别
        
        Args:
            image_path: 图像文件路径
            language: 输出语言
            
        Returns:
            产品识别结果
        """
        return await self._cached_analyze(
            self.gpt4v_service.recognize_product,
            image_path,
            'product_recognition',
            language
        )
    
    @with_error_handling()
    async def analyze_general(
        self,
        image_path: str,
        language: str = 'zh'
    ) -> Dict[str, Any]:
        """
        缓存增强的通用分析
        
        Args:
            image_path: 图像文件路径
            language: 输出语言
            
        Returns:
            通用分析结果
        """
        return await self._cached_analyze(
            self.gpt4v_service.analyze_general,
            image_path,
            'general_analysis',
            language
        )
    
    async def _cached_analyze(
        self,
        analyze_func: Callable,
        image_path: str,
        analysis_type: str,
        language: str
    ) -> Dict[str, Any]:
        """通用的缓存分析方法"""
        start_time = datetime.now()
        self.performance_stats['total_requests'] += 1
        
        try:
            # 读取图像文件内容用于缓存键生成
            async with aiofiles.open(image_path, 'rb') as f:
                image_content = await f.read()
            
            # 检查缓存
            if self.cache_enabled:
                cached_result = await self.cache.get_image_analysis(
                    image_content, analysis_type, language
                )
                
                if cached_result:
                    self.performance_stats['cache_hits'] += 1
                    
                    # 添加缓存指示器
                    cached_result['from_cache'] = True
                    cached_result['cache_hit_time'] = get_current_datetime()
                    
                    cache_time = get_processing_time_ms(start_time)
                    self.performance_stats['cache_save_time_ms'] += cache_time
                    
                    self.logger.debug(f"图像分析缓存命中，节省处理时间: {cache_time}ms")
                    return cached_result
            
            # 缓存未命中，调用原始服务
            self.performance_stats['cache_misses'] += 1
            result = await analyze_func(image_path, language)
            
            # 保存到缓存（如果置信度足够）
            if self.cache_enabled and result.get('overall_confidence', 0) > 0.4:
                await self.cache.cache_image_analysis(
                    image_content,
                    analysis_type,
                    language,
                    result
                )
            
            result['from_cache'] = False
            processing_time = get_processing_time_ms(start_time)
            
            self.logger.debug(f"图像分析完成，处理时间: {processing_time}ms")
            return result
            
        except Exception as e:
            self.logger.error(f"缓存增强的图像分析失败: {e}")
            raise


class CachedMultiModalProcessor(CachedMultiModalService):
    """缓存增强的多模态处理器"""
    
    def __init__(self, processor, cache: MultiModalCache):
        super().__init__(cache, "multimodal_processor")
        self.processor = processor
        
        # 替换子服务为缓存增强版本
        self.processor.whisper_service = CachedWhisperService(
            self.processor.whisper_service, cache
        )
        self.processor.gpt4v_service = CachedGPT4VService(
            self.processor.gpt4v_service, cache
        )
    
    @with_error_handling()
    async def process_multimodal_message(
        self,
        message,
        agent_context: Optional[Dict[str, Any]] = None
    ):
        """
        缓存增强的多模态消息处理
        
        Args:
            message: 多模态消息
            agent_context: 智能体上下文
            
        Returns:
            处理结果
        """
        start_time = datetime.now()
        self.performance_stats['total_requests'] += 1
        
        try:
            # 生成消息指纹用于缓存
            if self.cache_enabled and not message.attachments:
                # 纯文本消息可以考虑缓存
                message_fingerprint = self._generate_message_fingerprint(message)
                
                cached_result = await self.cache.get_multimodal_result(
                    {'message_fingerprint': message_fingerprint}
                )
                
                if cached_result:
                    self.performance_stats['cache_hits'] += 1
                    cached_result['from_cache'] = True
                    
                    cache_time = get_processing_time_ms(start_time)
                    self.performance_stats['cache_save_time_ms'] += cache_time
                    
                    self.logger.debug(f"多模态处理缓存命中，节省时间: {cache_time}ms")
                    return cached_result
            
            # 调用原始处理器（其中的子服务已经是缓存增强版本）
            self.performance_stats['cache_misses'] += 1
            result = await self.processor.process_multimodal_message(
                message, agent_context
            )
            
            # 缓存简单的处理结果
            if (self.cache_enabled and 
                not message.attachments and 
                not result.has_processing_errors()):
                
                message_fingerprint = self._generate_message_fingerprint(message)
                await self.cache.cache_multimodal_result(
                    {'message_fingerprint': message_fingerprint},
                    result.dict()
                )
            
            result_dict = result if isinstance(result, dict) else result.dict()
            result_dict['from_cache'] = False
            
            processing_time = get_processing_time_ms(start_time)
            self.logger.debug(f"多模态处理完成，处理时间: {processing_time}ms")
            
            return result
            
        except Exception as e:
            self.logger.error(f"缓存增强的多模态处理失败: {e}")
            raise
    
    def _generate_message_fingerprint(self, message) -> str:
        """生成消息指纹"""
        fingerprint_data = {
            'tenant_id': message.tenant_id,
            'customer_id': message.customer_id,
            'payload': message.payload,
            'context': {k: v for k, v in message.context.items() if k != 'timestamp'}
        }
        
        import json
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()


def cache_performance_monitor(func):
    """缓存性能监控装饰器"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = datetime.now()
        
        try:
            result = await func(self, *args, **kwargs)
            
            # 记录性能指标
            processing_time = get_processing_time_ms(start_time)
            
            if hasattr(self, 'performance_stats'):
                if result.get('from_cache', False):
                    self.performance_stats['processing_time_saved_ms'] += processing_time
                
                # 定期输出统计信息
                if self.performance_stats['total_requests'] % 100 == 0:
                    await self._log_performance_stats()
            
            return result
            
        except Exception as e:
            self.logger.error(f"缓存性能监控捕获异常: {e}")
            raise
    
    return wrapper


class CacheAwareServiceFactory:
    """缓存感知的服务工厂"""
    
    def __init__(self, cache: MultiModalCache):
        self.cache = cache
    
    def create_whisper_service(self, whisper_service):
        """创建缓存增强的Whisper服务"""
        return CachedWhisperService(whisper_service, self.cache)
    
    def create_gpt4v_service(self, gpt4v_service):
        """创建缓存增强的GPT-4V服务"""
        return CachedGPT4VService(gpt4v_service, self.cache)
    
    def create_multimodal_processor(self, processor):
        """创建缓存增强的多模态处理器"""
        return CachedMultiModalProcessor(processor, self.cache)


# 缓存策略配置
CACHE_STRATEGIES = {
    'aggressive': {
        'voice_min_confidence': 0.3,
        'image_min_confidence': 0.3,
        'cache_failures': True,
        'ttl_multiplier': 1.5
    },
    'conservative': {
        'voice_min_confidence': 0.7,
        'image_min_confidence': 0.6,
        'cache_failures': False,
        'ttl_multiplier': 1.0
    },
    'balanced': {
        'voice_min_confidence': 0.5,
        'image_min_confidence': 0.4,
        'cache_failures': False,
        'ttl_multiplier': 1.2
    }
}


async def configure_cache_strategy(
    cache: MultiModalCache,
    strategy: str = 'balanced'
) -> Dict[str, Any]:
    """
    配置缓存策略
    
    Args:
        cache: 缓存管理器
        strategy: 策略名称
        
    Returns:
        配置结果
    """
    if strategy not in CACHE_STRATEGIES:
        raise ValueError(f"Unknown cache strategy: {strategy}")
    
    config = CACHE_STRATEGIES[strategy]
    
    # 更新缓存配置
    for cache_type, cache_config in cache.cache_config.items():
        cache_config['ttl'] = int(cache_config['ttl'] * config['ttl_multiplier'])
    
    return {
        'strategy': strategy,
        'config': config,
        'applied_at': get_current_datetime()
    }