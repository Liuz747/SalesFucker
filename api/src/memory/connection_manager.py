"""
数据库连接管理模块

管理Elasticsearch和Redis连接，实现连接池和索引管理。
提供多租户支持和连接复用。

核心功能:
- Elasticsearch连接管理
- Redis连接管理
- 索引自动创建和优化
- 多租户连接池
"""

import asyncio
from typing import Dict, Optional
import aioredis
from elasticsearch import AsyncElasticsearch
from utils import get_component_logger


class DatabaseConnectionManager:
    """
    数据库连接管理器
    
    统一管理Elasticsearch和Redis连接，
    提供连接初始化和清理功能。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 数据库客户端
        self._es_client: Optional[AsyncElasticsearch] = None
        self._redis_client: Optional[aioredis.Redis] = None
    
    async def initialize_elasticsearch(self, elasticsearch_url: str) -> AsyncElasticsearch:
        """初始化Elasticsearch连接"""
        try:
            self._es_client = AsyncElasticsearch([elasticsearch_url])
            await self._ensure_indices()
            
            self.logger.info(f"Elasticsearch连接初始化完成: {self.tenant_id}")
            return self._es_client
            
        except Exception as e:
            self.logger.error(f"Elasticsearch初始化失败: {e}")
            raise
    
    async def initialize_redis(self, redis_url: str) -> aioredis.Redis:
        """初始化Redis连接"""
        try:
            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            
            self.logger.info(f"Redis连接初始化完成: {self.tenant_id}")
            return self._redis_client
            
        except Exception as e:
            self.logger.error(f"Redis初始化失败: {e}")
            raise
    
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
    
    @property
    def es_client(self) -> Optional[AsyncElasticsearch]:
        """获取Elasticsearch客户端"""
        return self._es_client
    
    @property
    def redis_client(self) -> Optional[aioredis.Redis]:
        """获取Redis客户端"""
        return self._redis_client
    
    async def cleanup(self):
        """清理数据库连接"""
        if self._es_client:
            await self._es_client.close()
        if self._redis_client:
            await self._redis_client.close()
        
        self.logger.info(f"数据库连接已清理: {self.tenant_id}")


class ConnectionPoolManager:
    """
    数据库连接池管理器
    
    管理多租户的数据库连接，实现连接复用和负载均衡。
    使用单例模式管理整个应用的连接池。
    """
    
    _instances: Dict[str, DatabaseConnectionManager] = {}
    _locks: Dict[str, asyncio.Lock] = {}
    
    @classmethod
    async def get_connection_manager(
        cls, 
        tenant_id: str, 
        elasticsearch_url: str, 
        redis_url: str
    ) -> DatabaseConnectionManager:
        """获取或创建数据库连接管理器"""
        if tenant_id not in cls._locks:
            cls._locks[tenant_id] = asyncio.Lock()
        
        async with cls._locks[tenant_id]:
            if tenant_id not in cls._instances:
                manager = DatabaseConnectionManager(tenant_id)
                await manager.initialize_elasticsearch(elasticsearch_url)
                await manager.initialize_redis(redis_url)
                cls._instances[tenant_id] = manager
            
            return cls._instances[tenant_id]
    
    @classmethod
    async def cleanup_all(cls):
        """清理所有连接管理器"""
        cleanup_tasks = [
            manager.cleanup() for manager in cls._instances.values()
        ]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        cls._instances.clear()
        cls._locks.clear()
    
    @classmethod
    def get_all_tenants(cls) -> list:
        """获取所有租户ID"""
        return list(cls._instances.keys())
    
    @classmethod
    async def cleanup_tenant(cls, tenant_id: str):
        """清理指定租户的连接"""
        if tenant_id in cls._instances:
            await cls._instances[tenant_id].cleanup()
            del cls._instances[tenant_id]
            if tenant_id in cls._locks:
                del cls._locks[tenant_id]
