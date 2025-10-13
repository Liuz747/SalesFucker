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
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import aiofiles

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin
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
