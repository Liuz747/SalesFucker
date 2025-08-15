"""
多模态缓存管理模块

该模块提供多模态处理结果的缓存管理功能。
支持语音转录、图像分析结果的高效缓存和检索。

核心功能:
- 多层次缓存架构（内存+Redis）
- 语音转录结果缓存
- 图像分析结果缓存
- 智能缓存失效策略
"""

import asyncio
import hashlib
import json
import pickle
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis

from utils import (
    get_current_datetime,
    LoggerMixin,
    with_error_handling,
    MultiModalConstants
)


class MultiModalCache(LoggerMixin):
    """
    多模态缓存管理器
    
    提供多层次缓存服务，优化多模态处理性能。
    
    属性:
        redis_client: Redis异步客户端
        memory_cache: 内存缓存
        cache_stats: 缓存统计信息
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        memory_cache_size: int = 1000
    ):
        """
        初始化多模态缓存管理器
        
        Args:
            redis_url: Redis连接URL
            memory_cache_size: 内存缓存大小
        """
        super().__init__()
        
        # Redis配置
        self.redis_client = None
        self.redis_url = redis_url
        
        # 内存缓存（LRU）
        self.memory_cache = {}
        self.memory_cache_order = []
        self.memory_cache_size = memory_cache_size
        
        # 缓存统计
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'redis_hits': 0,
            'memory_hits': 0,
            'total_requests': 0
        }
        
        # 缓存配置
        self.cache_config = {
            'voice_transcription': {
                'ttl': MultiModalConstants.VOICE_CACHE_TTL,
                'prefix': 'voice:',
                'use_memory': True
            },
            'image_analysis': {
                'ttl': MultiModalConstants.IMAGE_CACHE_TTL,
                'prefix': 'image:',
                'use_memory': True
            },
            'multimodal_result': {
                'ttl': 3600,  # 1小时
                'prefix': 'multimodal:',
                'use_memory': False  # 结果太大，不缓存到内存
            }
        }
        
        self.logger.info("多模态缓存管理器已初始化")
    
    async def initialize(self):
        """初始化缓存连接"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=False  # 支持二进制数据
            )
            
            # 测试连接
            await self.redis_client.ping()
            self.logger.info("Redis连接已建立")
            
        except Exception as e:
            self.logger.warning(f"Redis连接失败，使用仅内存缓存: {e}")
            self.redis_client = None
    
    @with_error_handling()
    async def cache_voice_transcription(
        self,
        audio_content: bytes,
        language: str,
        transcription_result: Dict[str, Any]
    ) -> str:
        """
        缓存语音转录结果
        
        Args:
            audio_content: 音频内容
            language: 语言代码
            transcription_result: 转录结果
            
        Returns:
            缓存键
        """
        cache_key = self._generate_voice_cache_key(audio_content, language)
        
        await self._set_cache(
            'voice_transcription',
            cache_key,
            transcription_result
        )
        
        self.logger.debug(f"语音转录结果已缓存: {cache_key}")
        return cache_key
    
    @with_error_handling()
    async def get_voice_transcription(
        self,
        audio_content: bytes,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的语音转录结果
        
        Args:
            audio_content: 音频内容
            language: 语言代码
            
        Returns:
            转录结果或None
        """
        cache_key = self._generate_voice_cache_key(audio_content, language)
        
        result = await self._get_cache('voice_transcription', cache_key)
        
        if result:
            self.logger.debug(f"语音转录缓存命中: {cache_key}")
        
        return result
    
    @with_error_handling()
    async def cache_image_analysis(
        self,
        image_content: bytes,
        analysis_type: str,
        language: str,
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        缓存图像分析结果
        
        Args:
            image_content: 图像内容
            analysis_type: 分析类型
            language: 语言代码
            analysis_result: 分析结果
            
        Returns:
            缓存键
        """
        cache_key = self._generate_image_cache_key(
            image_content, analysis_type, language
        )
        
        await self._set_cache(
            'image_analysis',
            cache_key,
            analysis_result
        )
        
        self.logger.debug(f"图像分析结果已缓存: {cache_key}")
        return cache_key
    
    @with_error_handling()
    async def get_image_analysis(
        self,
        image_content: bytes,
        analysis_type: str,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的图像分析结果
        
        Args:
            image_content: 图像内容
            analysis_type: 分析类型
            language: 语言代码
            
        Returns:
            分析结果或None
        """
        cache_key = self._generate_image_cache_key(
            image_content, analysis_type, language
        )
        
        result = await self._get_cache('image_analysis', cache_key)
        
        if result:
            self.logger.debug(f"图像分析缓存命中: {cache_key}")
        
        return result
    
    @with_error_handling()
    async def cache_multimodal_result(
        self,
        message_content: Dict[str, Any],
        processing_result: Dict[str, Any]
    ) -> str:
        """
        缓存多模态处理结果
        
        Args:
            message_content: 消息内容
            processing_result: 处理结果
            
        Returns:
            缓存键
        """
        cache_key = self._generate_multimodal_cache_key(message_content)
        
        await self._set_cache(
            'multimodal_result',
            cache_key,
            processing_result
        )
        
        self.logger.debug(f"多模态处理结果已缓存: {cache_key}")
        return cache_key
    
    @with_error_handling()
    async def get_multimodal_result(
        self,
        message_content: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的多模态处理结果
        
        Args:
            message_content: 消息内容
            
        Returns:
            处理结果或None
        """
        cache_key = self._generate_multimodal_cache_key(message_content)
        
        result = await self._get_cache('multimodal_result', cache_key)
        
        if result:
            self.logger.debug(f"多模态处理结果缓存命中: {cache_key}")
        
        return result
    
    def _generate_voice_cache_key(
        self,
        audio_content: bytes,
        language: str
    ) -> str:
        """生成语音缓存键"""
        content_hash = hashlib.sha256(audio_content).hexdigest()
        return f"voice:{language}:{content_hash}"
    
    def _generate_image_cache_key(
        self,
        image_content: bytes,
        analysis_type: str,
        language: str
    ) -> str:
        """生成图像缓存键"""
        content_hash = hashlib.sha256(image_content).hexdigest()
        return f"image:{analysis_type}:{language}:{content_hash}"
    
    def _generate_multimodal_cache_key(
        self,
        message_content: Dict[str, Any]
    ) -> str:
        """生成多模态缓存键"""
        # 创建内容指纹
        content_str = json.dumps(message_content, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        return f"multimodal:{content_hash}"
    
    async def _set_cache(
        self,
        cache_type: str,
        key: str,
        value: Any
    ):
        """设置缓存"""
        self.cache_stats['total_requests'] += 1
        
        config = self.cache_config.get(cache_type, {})
        ttl = config.get('ttl', 3600)
        prefix = config.get('prefix', '')
        use_memory = config.get('use_memory', True)
        
        full_key = f"{prefix}{key}"
        
        # 序列化数据
        serialized_value = pickle.dumps({
            'data': value,
            'cached_at': get_current_datetime(),
            'cache_type': cache_type
        })
        
        # Redis缓存
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    full_key,
                    ttl,
                    serialized_value
                )
            except Exception as e:
                self.logger.warning(f"Redis缓存设置失败: {e}")
        
        # 内存缓存
        if use_memory:
            await self._set_memory_cache(full_key, serialized_value, ttl)
    
    async def _get_cache(
        self,
        cache_type: str,
        key: str
    ) -> Optional[Any]:
        """获取缓存"""
        self.cache_stats['total_requests'] += 1
        
        config = self.cache_config.get(cache_type, {})
        prefix = config.get('prefix', '')
        use_memory = config.get('use_memory', True)
        
        full_key = f"{prefix}{key}"
        
        # 先查内存缓存
        if use_memory:
            memory_result = await self._get_memory_cache(full_key)
            if memory_result is not None:
                self.cache_stats['hits'] += 1
                self.cache_stats['memory_hits'] += 1
                return memory_result
        
        # 再查Redis缓存
        if self.redis_client:
            try:
                redis_result = await self.redis_client.get(full_key)
                if redis_result:
                    cached_data = pickle.loads(redis_result)
                    result = cached_data['data']
                    
                    # 回填内存缓存
                    if use_memory:
                        await self._set_memory_cache(
                            full_key,
                            redis_result,
                            config.get('ttl', 3600)
                        )
                    
                    self.cache_stats['hits'] += 1
                    self.cache_stats['redis_hits'] += 1
                    return result
                    
            except Exception as e:
                self.logger.warning(f"Redis缓存读取失败: {e}")
        
        self.cache_stats['misses'] += 1
        return None
    
    async def _set_memory_cache(
        self,
        key: str,
        value: bytes,
        ttl: int
    ):
        """设置内存缓存"""
        current_time = datetime.now()
        expire_time = current_time + timedelta(seconds=ttl)
        
        # 如果缓存已满，清理最旧的项
        if len(self.memory_cache) >= self.memory_cache_size:
            await self._evict_memory_cache()
        
        self.memory_cache[key] = {
            'data': value,
            'expire_time': expire_time,
            'access_time': current_time
        }
        
        # 更新访问顺序
        if key in self.memory_cache_order:
            self.memory_cache_order.remove(key)
        self.memory_cache_order.append(key)
    
    async def _get_memory_cache(self, key: str) -> Optional[Any]:
        """获取内存缓存"""
        if key not in self.memory_cache:
            return None
        
        cache_item = self.memory_cache[key]
        current_time = datetime.now()
        
        # 检查是否过期
        if current_time > cache_item['expire_time']:
            del self.memory_cache[key]
            if key in self.memory_cache_order:
                self.memory_cache_order.remove(key)
            return None
        
        # 更新访问时间和顺序
        cache_item['access_time'] = current_time
        if key in self.memory_cache_order:
            self.memory_cache_order.remove(key)
        self.memory_cache_order.append(key)
        
        # 反序列化数据
        try:
            cached_data = pickle.loads(cache_item['data'])
            return cached_data['data']
        except Exception as e:
            self.logger.warning(f"内存缓存反序列化失败: {e}")
            del self.memory_cache[key]
            return None
    
    async def _evict_memory_cache(self):
        """清理内存缓存"""
        # 删除最旧的缓存项
        if self.memory_cache_order:
            oldest_key = self.memory_cache_order.pop(0)
            if oldest_key in self.memory_cache:
                del self.memory_cache[oldest_key]
    
    @with_error_handling()
    async def invalidate_cache(
        self,
        cache_type: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        失效缓存
        
        Args:
            cache_type: 缓存类型
            pattern: 匹配模式
        """
        if cache_type and pattern:
            prefix = self.cache_config.get(cache_type, {}).get('prefix', '')
            full_pattern = f"{prefix}{pattern}"
        else:
            full_pattern = pattern or "*"
        
        # 清理Redis缓存
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(full_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    self.logger.info(f"Redis缓存已清理: {len(keys)} 个键")
            except Exception as e:
                self.logger.warning(f"Redis缓存清理失败: {e}")
        
        # 清理内存缓存
        if pattern:
            keys_to_remove = []
            for key in self.memory_cache:
                if pattern in key or pattern == "*":
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                if key in self.memory_cache_order:
                    self.memory_cache_order.remove(key)
            
            self.logger.info(f"内存缓存已清理: {len(keys_to_remove)} 个键")
    
    @with_error_handling()
    async def cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = datetime.now()
        expired_keys = []
        
        # 清理内存缓存中的过期项
        for key, cache_item in self.memory_cache.items():
            if current_time > cache_item['expire_time']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            if key in self.memory_cache_order:
                self.memory_cache_order.remove(key)
        
        if expired_keys:
            self.logger.info(f"清理过期内存缓存: {len(expired_keys)} 个键")
    
    @with_error_handling()
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = 0.0
        if self.cache_stats['total_requests'] > 0:
            hit_rate = self.cache_stats['hits'] / self.cache_stats['total_requests']
        
        redis_info = {}
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info('memory')
            except Exception:
                redis_info = {'error': 'Redis信息获取失败'}
        
        return {
            'hit_rate': hit_rate,
            'total_requests': self.cache_stats['total_requests'],
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'redis_hits': self.cache_stats['redis_hits'],
            'memory_hits': self.cache_stats['memory_hits'],
            'memory_cache_size': len(self.memory_cache),
            'memory_cache_limit': self.memory_cache_size,
            'redis_connected': self.redis_client is not None,
            'redis_info': redis_info,
            'cache_config': self.cache_config
        }
    
    @with_error_handling()
    async def warmup_cache(
        self,
        common_queries: List[Dict[str, Any]]
    ):
        """
        缓存预热
        
        Args:
            common_queries: 常见查询列表
        """
        self.logger.info(f"开始缓存预热，查询数量: {len(common_queries)}")
        
        for query in common_queries:
            try:
                # 这里可以根据查询类型进行预处理
                # 然后将结果放入缓存
                pass
            except Exception as e:
                self.logger.warning(f"缓存预热失败: {e}")
        
        self.logger.info("缓存预热完成")
    
    async def close(self):
        """关闭缓存连接"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                self.logger.info("Redis连接已关闭")
            except Exception as e:
                self.logger.warning(f"Redis连接关闭失败: {e}")
        
        # 清理内存缓存
        self.memory_cache.clear()
        self.memory_cache_order.clear()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            'status': 'healthy',
            'service': 'multimodal_cache',
            'memory_cache': {
                'status': 'healthy',
                'size': len(self.memory_cache),
                'limit': self.memory_cache_size
            },
            'redis_cache': {
                'status': 'unknown',
                'connected': False
            },
            'statistics': await self.get_cache_stats(),
            'timestamp': get_current_datetime()
        }
        
        # 检查Redis连接
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health_status['redis_cache']['status'] = 'healthy'
                health_status['redis_cache']['connected'] = True
            except Exception as e:
                health_status['redis_cache']['status'] = 'unhealthy'
                health_status['redis_cache']['error'] = str(e)
        
        return health_status


# 全局缓存实例（可配置为单例）
_cache_instance = None


async def get_multimodal_cache(
    redis_url: str = "redis://localhost:6379",
    memory_cache_size: int = 1000
) -> MultiModalCache:
    """获取多模态缓存实例"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = MultiModalCache(redis_url, memory_cache_size)
        await _cache_instance.initialize()
    
    return _cache_instance


async def close_multimodal_cache():
    """关闭多模态缓存"""
    global _cache_instance
    
    if _cache_instance is not None:
        await _cache_instance.close()
        _cache_instance = None