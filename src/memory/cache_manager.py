"""
多级缓存管理模块

提供本地缓存、Redis缓存的统一管理接口。
实现LRU策略和异步缓存更新机制。

核心功能:
- 本地内存缓存 (< 1ms)
- Redis分布式缓存 (< 10ms)
- 自动过期和LRU淘汰
- 异步缓存更新
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import aioredis
from src.utils import get_component_logger


class MultiLevelCacheManager:
    """
    多级缓存管理器
    
    实现本地缓存 + Redis缓存的两级存储策略，
    针对客户档案检索进行优化。
    """
    
    def __init__(self, tenant_id: str, config):
        self.tenant_id = tenant_id
        self.config = config
        self.logger = get_component_logger(__name__, tenant_id)
        
        # Redis客户端
        self._redis_client: Optional[aioredis.Redis] = None
        
        # 本地缓存
        self._local_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # 统计信息
        self._cache_hits = 0
        self._cache_misses = 0
        self._redis_operations = 0
    
    async def initialize(self, redis_url: str):
        """初始化Redis连接"""
        try:
            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            self.logger.info(f"缓存管理器初始化完成: {self.tenant_id}")
        except Exception as e:
            self.logger.error(f"缓存管理器初始化失败: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        多级缓存获取
        
        检索顺序:
        1. 本地缓存 (< 1ms)
        2. Redis缓存 (< 10ms)
        """
        # Level 1: 本地缓存
        cached_data = self._get_from_local_cache(key)
        if cached_data:
            self._cache_hits += 1
            return cached_data
        
        # Level 2: Redis缓存
        try:
            redis_data = await self._redis_client.get(key)
            if redis_data:
                data = json.loads(redis_data)
                self._update_local_cache(key, data)
                self._cache_hits += 1
                self._redis_operations += 1
                return data
        except Exception as e:
            self.logger.warning(f"Redis查询失败: {e}")
        
        self._cache_misses += 1
        return None
    
    async def set(self, key: str, data: Dict[str, Any]):
        """设置缓存数据"""
        # 立即更新本地缓存
        self._update_local_cache(key, data)
        
        # 异步更新Redis
        asyncio.create_task(self._update_redis(key, data))
    
    async def batch_get(self, keys: list) -> Dict[str, Dict[str, Any]]:
        """批量获取缓存数据"""
        results = {}
        cache_misses = []
        
        # 1. 批量检查本地缓存
        for key in keys:
            cached = self._get_from_local_cache(key)
            if cached:
                results[key] = cached
                self._cache_hits += 1
            else:
                cache_misses.append(key)
        
        if not cache_misses:
            return results
        
        # 2. 批量Redis查询
        try:
            redis_results = await self._redis_client.mget(cache_misses)
            
            for i, redis_data in enumerate(redis_results):
                key = cache_misses[i]
                if redis_data:
                    data = json.loads(redis_data)
                    results[key] = data
                    self._update_local_cache(key, data)
                    self._cache_hits += 1
            
            self._redis_operations += 1
            
        except Exception as e:
            self.logger.warning(f"批量Redis查询失败: {e}")
        
        return results
    
    def _get_from_local_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """从本地缓存获取数据"""
        if key in self._local_cache:
            # 检查是否过期
            if key in self._cache_timestamps:
                age = datetime.utcnow() - self._cache_timestamps[key]
                if age.total_seconds() > self.config.redis_ttl:
                    del self._local_cache[key]
                    del self._cache_timestamps[key]
                    return None
            
            return self._local_cache[key]
        return None
    
    def _update_local_cache(self, key: str, data: Dict[str, Any]):
        """更新本地缓存"""
        # LRU策略 - 如果缓存满了删除最旧的
        if len(self._local_cache) >= self.config.local_cache_size:
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._local_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._local_cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()
    
    async def _update_redis(self, key: str, data: Dict[str, Any]):
        """异步更新Redis缓存"""
        try:
            await self._redis_client.setex(
                key, 
                self.config.redis_ttl, 
                json.dumps(data, ensure_ascii=False)
            )
            self._redis_operations += 1
        except Exception as e:
            self.logger.warning(f"Redis更新失败: {e}")
    
    async def update_both_caches(self, key: str, data: Dict[str, Any]):
        """同时更新本地缓存和Redis缓存"""
        self._update_local_cache(key, data)
        await self._update_redis(key, data)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        cache_hit_rate = 0.0
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            cache_hit_rate = (self._cache_hits / total_requests) * 100
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "redis_operations": self._redis_operations,
            "local_cache_size": len(self._local_cache),
            "max_local_cache_size": self.config.local_cache_size
        }
    
    async def cleanup(self):
        """清理缓存资源"""
        if self._redis_client:
            await self._redis_client.close()
        
        self._local_cache.clear()
        self._cache_timestamps.clear()
        
        self.logger.info(f"缓存管理器已清理: {self.tenant_id}")
