"""
基础设施客户端类型定义。

提供统一的 dataclass 用于传递集中初始化的外部服务客户端。
"""

from dataclasses import dataclass

from elasticsearch import AsyncElasticsearch
from pymilvus import MilvusClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class InfraClients:
    """集中封装数据库、缓存和搜索等基础设施客户端，供运行时复用。"""

    db_engine: AsyncEngine
    redis: Redis
    elasticsearch: AsyncElasticsearch | None
    milvus: MilvusClient | None
