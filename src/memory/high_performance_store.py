"""
高性能内存存储模块

提供生产级的客户档案和对话历史存储解决方案。
针对多租户场景优化，支持Elasticsearch和Redis集成。

核心优化:
- 异步批量操作
- 多级缓存策略  
- 连接池管理
- 查询优化
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import asynccontextmanager
import aioredis
from elasticsearch import AsyncElasticsearch
from utils import get_component_logger


@dataclass
class CacheConfig:
    """缓存配置"""
    redis_ttl: int = 3600  # 1小时
    local_cache_size: int = 1000
    batch_size: int = 50
    flush_interval: int = 300  # 5分钟


class HighPerformanceStore:
    """
    高性能数据存储引擎
    
    设计目标:
    - 客户档案检索 < 50ms
    - 批量写入支持 1000+ TPS
    - 99.9% 可用性
    - 多租户数据隔离
    """
    
    def __init__(self, tenant_id: str, config: CacheConfig = None):
        self.tenant_id = tenant_id
        self.config = config or CacheConfig()
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 连接池和客户端
        self._es_client: Optional[AsyncElasticsearch] = None
        self._redis_client: Optional[aioredis.Redis] = None
        
        # 多级缓存
        self._local_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._write_buffer: List[Dict[str, Any]] = []
        
        # 性能监控
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "elasticsearch_queries": 0,
            "redis_operations": 0,
            "batch_writes": 0
        }
        
        # 批量写入任务
        self._batch_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self, elasticsearch_url: str, redis_url: str):
        """初始化数据库连接"""
        try:
            # Elasticsearch连接
            self._es_client = AsyncElasticsearch([elasticsearch_url])
            await self._ensure_indices()
            
            # Redis连接
            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            
            # 启动批量写入任务
            self._batch_task = asyncio.create_task(self._batch_write_worker())
            
            self.logger.info(f"高性能存储引擎初始化完成: {self.tenant_id}")
            
        except Exception as e:
            self.logger.error(f"存储引擎初始化失败: {e}")
            raise
    
    async def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        高性能客户档案检索
        
        检索策略:
        1. 本地缓存 (< 1ms)
        2. Redis缓存 (< 10ms) 
        3. Elasticsearch (< 50ms)
        """
        cache_key = f"profile:{self.tenant_id}:{customer_id}"
        
        # Level 1: 本地缓存
        cached_profile = self._get_from_local_cache(cache_key)
        if cached_profile:
            self._stats["cache_hits"] += 1
            return cached_profile
        
        # Level 2: Redis缓存
        try:
            redis_data = await self._redis_client.get(cache_key)
            if redis_data:
                profile = json.loads(redis_data)
                self._update_local_cache(cache_key, profile)
                self._stats["cache_hits"] += 1
                self._stats["redis_operations"] += 1
                return profile
        except Exception as e:
            self.logger.warning(f"Redis查询失败: {e}")
        
        # Level 3: Elasticsearch
        try:
            es_result = await self._es_client.get(
                index=f"{self.tenant_id}_profiles",
                id=customer_id,
                ignore=[404]
            )
            
            if es_result.get("found"):
                profile = es_result["_source"]
                
                # 异步更新缓存
                asyncio.create_task(self._update_caches(cache_key, profile))
                
                self._stats["cache_misses"] += 1
                self._stats["elasticsearch_queries"] += 1
                return profile
                
        except Exception as e:
            self.logger.error(f"Elasticsearch查询失败: {e}")
        
        self._stats["cache_misses"] += 1
        return None
    
    async def update_customer_profile(self, customer_id: str, profile_data: Dict[str, Any]):
        """
        异步档案更新
        
        使用写入缓冲区实现批量写入优化
        """
        cache_key = f"profile:{self.tenant_id}:{customer_id}"
        
        # 立即更新缓存
        self._update_local_cache(cache_key, profile_data)
        
        # 异步更新Redis
        asyncio.create_task(self._update_redis(cache_key, profile_data))
        
        # 添加到批量写入缓冲区
        write_operation = {
            "operation": "update_profile",
            "customer_id": customer_id,
            "data": profile_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._write_buffer.append(write_operation)
        
        # 如果缓冲区满了，立即触发批量写入
        if len(self._write_buffer) >= self.config.batch_size:
            await self._flush_write_buffer()
    
    async def batch_get_profiles(self, customer_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取客户档案 - 高度优化
        """
        results = {}
        cache_misses = []
        
        # 1. 批量检查本地缓存
        for customer_id in customer_ids:
            cache_key = f"profile:{self.tenant_id}:{customer_id}"
            cached = self._get_from_local_cache(cache_key)
            if cached:
                results[customer_id] = cached
                self._stats["cache_hits"] += 1
            else:
                cache_misses.append((customer_id, cache_key))
        
        if not cache_misses:
            return results
        
        # 2. 批量Redis查询
        redis_keys = [cache_key for _, cache_key in cache_misses]
        try:
            redis_results = await self._redis_client.mget(redis_keys)
            remaining_misses = []
            
            for i, redis_data in enumerate(redis_results):
                customer_id, cache_key = cache_misses[i]
                if redis_data:
                    profile = json.loads(redis_data)
                    results[customer_id] = profile
                    self._update_local_cache(cache_key, profile)
                    self._stats["cache_hits"] += 1
                else:
                    remaining_misses.append(customer_id)
            
            self._stats["redis_operations"] += 1
            
        except Exception as e:
            self.logger.warning(f"批量Redis查询失败: {e}")
            remaining_misses = [customer_id for customer_id, _ in cache_misses]
        
        # 3. 批量Elasticsearch查询
        if remaining_misses:
            try:
                es_queries = []
                for customer_id in remaining_misses:
                    es_queries.append({
                        "_index": f"{self.tenant_id}_profiles",
                        "_id": customer_id
                    })
                
                es_response = await self._es_client.mget(body={"docs": es_queries})
                
                for doc in es_response["docs"]:
                    if doc.get("found"):
                        customer_id = doc["_id"]
                        profile = doc["_source"]
                        results[customer_id] = profile
                        
                        # 异步更新缓存
                        cache_key = f"profile:{self.tenant_id}:{customer_id}"
                        asyncio.create_task(self._update_caches(cache_key, profile))
                
                self._stats["elasticsearch_queries"] += 1
                
            except Exception as e:
                self.logger.error(f"批量Elasticsearch查询失败: {e}")
        
        return results
    
    async def _batch_write_worker(self):
        """批量写入工作线程"""
        while not self._shutdown_event.is_set():
            try:
                # 等待写入间隔或关闭信号
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.config.flush_interval
                )
            except asyncio.TimeoutError:
                # 超时 - 执行批量写入
                if self._write_buffer:
                    await self._flush_write_buffer()
    
    async def _flush_write_buffer(self):
        """刷新写入缓冲区到Elasticsearch"""
        if not self._write_buffer:
            return
        
        operations = self._write_buffer.copy()
        self._write_buffer.clear()
        
        try:
            # 构建批量操作
            bulk_operations = []
            for op in operations:
                if op["operation"] == "update_profile":
                    bulk_operations.extend([
                        {
                            "update": {
                                "_index": f"{self.tenant_id}_profiles",
                                "_id": op["customer_id"]
                            }
                        },
                        {
                            "doc": op["data"],
                            "doc_as_upsert": True
                        }
                    ])
            
            if bulk_operations:
                response = await self._es_client.bulk(body=bulk_operations)
                
                if response.get("errors"):
                    self.logger.warning(f"批量写入部分失败: {len([item for item in response['items'] if 'error' in item])}")
                
                self._stats["batch_writes"] += 1
                self.logger.debug(f"批量写入完成: {len(operations)}条记录")
        
        except Exception as e:
            self.logger.error(f"批量写入失败: {e}")
            # 重新添加到缓冲区重试
            self._write_buffer.extend(operations[:10])  # 只重试前10条
    
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
            self._stats["redis_operations"] += 1
        except Exception as e:
            self.logger.warning(f"Redis更新失败: {e}")
    
    async def _update_caches(self, key: str, data: Dict[str, Any]):
        """同时更新本地缓存和Redis缓存"""
        self._update_local_cache(key, data)
        await self._update_redis(key, data)
    
    async def _ensure_indices(self):
        """确保Elasticsearch索引存在"""
        index_name = f"{self.tenant_id}_profiles"
        
        if not await self._es_client.indices.exists(index=index_name):
            # 创建优化的索引映射
            mapping = {
                "mappings": {
                    "properties": {
                        "customer_id": {"type": "keyword"},
                        "profile": {"type": "object", "enabled": True},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "tenant_id": {"type": "keyword"}
                    }
                },
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "5s"  # 优化写入性能
                }
            }
            
            await self._es_client.indices.create(index=index_name, body=mapping)
            self.logger.info(f"创建Elasticsearch索引: {index_name}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_hit_rate = 0.0
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        if total_requests > 0:
            cache_hit_rate = (self._stats["cache_hits"] / total_requests) * 100
        
        return {
            "tenant_id": self.tenant_id,
            "cache_hit_rate": cache_hit_rate,
            "total_requests": total_requests,
            "pending_writes": len(self._write_buffer),
            "performance_stats": self._stats.copy(),
            "cache_sizes": {
                "local_cache": len(self._local_cache),
                "max_local_cache": self.config.local_cache_size
            }
        }
    
    async def cleanup(self):
        """清理资源"""
        # 停止批量写入任务
        self._shutdown_event.set()
        if self._batch_task:
            await self._batch_task
        
        # 刷新剩余的写入操作
        await self._flush_write_buffer()
        
        # 关闭连接
        if self._es_client:
            await self._es_client.close()
        if self._redis_client:
            await self._redis_client.close()
        
        self.logger.info(f"高性能存储引擎已清理: {self.tenant_id}")


class ConnectionPoolManager:
    """
    数据库连接池管理器
    
    管理多租户的数据库连接，实现连接复用和负载均衡
    """
    
    _instances: Dict[str, HighPerformanceStore] = {}
    _locks: Dict[str, asyncio.Lock] = {}
    
    @classmethod
    async def get_store(cls, tenant_id: str, elasticsearch_url: str, redis_url: str) -> HighPerformanceStore:
        """获取或创建高性能存储实例"""
        if tenant_id not in cls._locks:
            cls._locks[tenant_id] = asyncio.Lock()
        
        async with cls._locks[tenant_id]:
            if tenant_id not in cls._instances:
                store = HighPerformanceStore(tenant_id)
                await store.initialize(elasticsearch_url, redis_url)
                cls._instances[tenant_id] = store
            
            return cls._instances[tenant_id]
    
    @classmethod
    async def cleanup_all(cls):
        """清理所有存储实例"""
        cleanup_tasks = [
            store.cleanup() for store in cls._instances.values()
        ]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        cls._instances.clear()
        cls._locks.clear()