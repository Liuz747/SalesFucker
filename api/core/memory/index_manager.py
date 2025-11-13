"""
Hybrid Memory System - Elasticsearch索引管理

创建和管理memory_v1索引，支持：
- 密集向量存储
- 全文检索和语义搜索
- 多租户数据隔离
- 时间范围查询和TTL管理
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError

from config import mas_config
from libs.factory import infra_registry
from utils import get_component_logger, to_isoformat

logger = get_component_logger(__name__)


class ElasticsearchIndex:
    """
    Memory索引管理器

    负责memory_v1索引的创建、更新和维护。
    支持向量检索、全文搜索和混合查询。
    """

    def __init__(self):
        self._es_client: Optional[AsyncElasticsearch] = None
        self.index_name = mas_config.ES_MEMORY_INDEX

    @property
    def client(self) -> AsyncElasticsearch:
        """获取集中管理的 Elasticsearch 客户端。"""
        if self._es_client is None:
            clients = infra_registry.get_cached_clients()
            if clients is None or clients.elasticsearch is None:
                raise RuntimeError("Elasticsearch客户端未初始化，请先调用 infra_registry.create_clients()")
            self._es_client = clients.elasticsearch
        return self._es_client

    async def create_memory_index(self, force_recreate: bool = False) -> bool:
        """
        创建memory_v1索引

        索引特性：
        - dense_vector字段支持kNN语义搜索
        - text字段支持全文检索
        - 多租户隔离字段
        - 时间戳和TTL支持

        Args:
            force_recreate: 是否强制重建索引（会删除现有数据）

        Returns:
            bool: 创建成功返回True
        """
        try:
            # 检查索引是否已存在
            exists = await self.client.indices.exists(index=self.index_name)

            if exists:
                if force_recreate:
                    logger.warning(f"删除现有索引: {self.index_name}")
                    await self.client.indices.delete(index=self.index_name)
                else:
                    logger.info(f"索引已存在: {self.index_name}")
                    return True

            # 定义索引映射
            index_mapping = {
                "settings": {
                    "number_of_shards": mas_config.ES_NUMBER_OF_SHARDS,
                    "number_of_replicas": 1,
                    "refresh_interval": mas_config.ES_REFRESH_INTERVAL,
                    "index": {
                        "max_result_window": 10000,  # 最大分页深度
                    },
                    "analysis": {
                        "analyzer": {
                            "ik_max_word": {"type": "ik_max_word"},
                            "ik_smart": {"type": "ik_smart"}
                        }
                    }
                },
                "mappings": {
                    "dynamic": False,
                    "properties": {
                        # 核心字段
                        "tenant_id": {"type": "keyword"},
                        "thread_id": {"type": "keyword",},
                        # 记忆内容
                        "content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        # 向量嵌入 - 关键字段
                        "embedding": {
                            "type": "dense_vector",
                            "dims": mas_config.ES_VECTOR_DIMENSION,
                            "index": False
                        },
                        # 元数据
                        "memory_type": {"type": "keyword"},  # short_term, long_term, episodic, semantic
                        "importance_score": {"type": "float", "doc_values": False},  # 0.0-1.0
                        "access_count": {"type": "integer", "doc_values": False},
                        "last_accessed_at": {"type": "date"},
                        "created_at": {"type": "date"},
                        "expires_at": {"type": "date"},
                        # 关联信息
                        "tags": {"type": "keyword"},
                        "entities": {
                            "type": "object",
                            "enabled": True,
                        },
                        # 检索元数据
                        "metadata": {
                            "type": "object",
                            "enabled": False,  # 不索引，仅存储
                        },
                    }
                },
            }

            # 创建索引
            response = await self.client.indices.create(index=self.index_name, **index_mapping)

            # wait cluster ready
            await self.client.cluster.health(index=self.index_name, wait_for_status="yellow")


            logger.info(f"索引创建成功: {self.index_name} - {response}")
            return True

        except Exception as e:
            logger.error(f"索引创建失败: {e}")
            return False

    # --------------------------------------------------------------------
    # Insert summary entry
    # --------------------------------------------------------------------
    async def store_summary(
        self,
        tenant_id: str,
        thread_id: UUID,
        content: str,
        memory_type: str = "mid_term",
        expires_at: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Insert a summary document into Elasticsearch.

        Returns:
            Document ID
        """
        doc = {
            "tenant_id": tenant_id,
            "thread_id": str(thread_id),
            "content": content,
            "memory_type": memory_type,
            "created_at": to_isoformat(),
            "last_accessed_at": None,
            "expires_at": to_isoformat(expires_at) if expires_at else None,
            "tags": tags or [],
            "entities": {},
            "importance_score": None,
            "access_count": 0,
            "metadata": metadata or {},
        }

        try:
            result = await self.client.index(index=self.index_name, document=doc)
            doc_id = result["_id"]
            logger.debug(f"[ElasticsearchIndex] Created summary doc: {doc_id}")
            return doc_id

        except Exception as e:
            logger.exception(f"[ElasticsearchIndex] Failed to store summary: {e}")
            raise

    # --------------------------------------------------------------------
    # Get all summaries for a thread (sorted)
    # --------------------------------------------------------------------
    async def get_thread_summaries(
        self,
        tenant_id: str,
        thread_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """
        Fetch summaries for a given thread.
        """
        query = {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": tenant_id}},
                    {"term": {"thread_id": str(thread_id)}},
                ]
            }
        }

        try:
            res = await self.client.search(
                index=self.index_name,
                query=query,
                sort=[{"created_at": {"order": "asc"}}],
                size=limit,
            )
            return [hit["_source"] | {"id": hit["_id"]} for hit in res["hits"]["hits"]]

        except NotFoundError:
            return []
        except Exception as e:
            logger.exception(f"[ElasticsearchIndex] Failed to get thread summaries: {e}")
            return []

    # --------------------------------------------------------------------
    # General search
    # --------------------------------------------------------------------
    async def search(
        self,
        tenant_id: str,
        query_text: str,
        thread_id: UUID,
        limit: int = 5,
    ) -> list[dict]:
        """
        Keyword search using full-text match + tenant/thread filters.
        """
        filters = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"thread_id": str(thread_id)}},
        ]

        query = {
            "bool": {
                "must": [{"match": {"content": query_text}}],
                "filter": filters,
            }
        }

        try:
            res = await self.client.search(
                index=self.index_name,
                query=query,
                sort=[{"created_at": {"order": "desc"}}],
                size=limit,
            )
            return [hit["_source"] | {"id": hit["_id"]} for hit in res["hits"]["hits"]]

        except Exception as e:
            logger.exception(f"[ElasticsearchIndex] Search failed: {e}")
            return []

    # --------------------------------------------------------------------
    # Update access metadata
    # --------------------------------------------------------------------
    async def update_access_metadata(
        self,
        doc_id: str,
        access_count: Optional[int] = None,
    ):
        """
        Update access_count and last_accessed_at.
        """
        body = {"doc": {"last_accessed_at": to_isoformat()}}
        if access_count is not None:
            body["doc"]["access_count"] = access_count

        try:
            await self.client.update(
                index=self.index_name,
                id=doc_id,
                body=body,
            )
        except Exception as e:
            logger.warning(f"[ElasticsearchIndex] Failed to update metadata: {e}")

    # --------------------------------------------------------------------
    # Delete expired memory entries
    # --------------------------------------------------------------------
    async def delete_expired(self):
        """
        Delete all documents whose expires_at < now().
        """
        query = {
            "range": {
                "expires_at": {"lt": "now"}
            }
        }

        try:
            res = await self.client.delete_by_query(
                index=self.index_name,
                query=query,
                conflicts="proceed"
            )
            logger.info(f"[ElasticsearchIndex] Deleted expired docs: {res['deleted']}")

        except Exception as e:
            logger.error(f"[ElasticsearchIndex] Failed to delete expired docs: {e}")
