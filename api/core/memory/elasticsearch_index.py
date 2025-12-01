"""
Hybrid Memory System - Elasticsearch索引管理

创建和管理memory_v1索引，支持混合记忆架构：
- 文本内容存储和全文检索（使用IK分词器）
- 元数据管理和过滤查询
- 向量嵌入存储
- 多租户数据隔离
- 时间范围查询和TTL管理
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError

from config import mas_config
from libs.factory import infra_registry
from libs.types import MemoryType
from utils import get_component_logger, to_isoformat

logger = get_component_logger(__name__)


class ElasticsearchIndex:
    """
    Memory索引管理器

    负责memory_v1索引的创建、更新和维护。
    专注于文本搜索、元数据管理和记忆存储。
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

    # --------------------------------------------------------------------
    # Insert summary entry
    # --------------------------------------------------------------------
    async def store_summary(
        self,
        tenant_id: str,
        thread_id: UUID,
        content: str,
        memory_type: MemoryType,
        importance_score: Optional[float] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """
        向Elasticsearch插入摘要文档

        Args:
            tenant_id: 租户ID
            thread_id: 对话线程ID
            content: 记忆内容
            memory_type: 记忆类型 (MemoryType enum)
            expires_at: 过期时间（可选）
            tags: 标签列表（可选）
            metadata: 元数据字典（可选）
            importance_score: 重要性评分（可选）

        Returns:
            str: 文档ID
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
            "importance_score": importance_score,
            "access_count": 0,
            "metadata": metadata or {},
        }

        try:
            result = await self.client.index(index=self.index_name, document=doc)
            doc_id = result["_id"]
            logger.debug(f"[ElasticsearchIndex] Created memory doc ({memory_type}): {doc_id}")
            return doc_id

        except Exception as e:
            logger.exception(f"[ElasticsearchIndex] Failed to store memory ({memory_type}): {e}")
            raise

    # --------------------------------------------------------------------
    # 按 thread 获取摘要列表
    # --------------------------------------------------------------------
    async def get_thread_summaries(
        self,
        tenant_id: str,
        thread_id: UUID,
        limit: int = 20,
        memory_type: MemoryType = MemoryType.LONG_TERM,
    ) -> list[dict]:
        """
        获取指定对话线程的所有摘要

        Args:
            tenant_id: 租户ID
            thread_id: 对话线程ID
            limit: 返回结果数量限制，默认20
            memory_types: 需要的记忆类型过滤（默认仅long term）

        Returns:
            list[dict]: 摘要列表，按创建时间降序排列
        """
        filters = [
            {"term": {"tenant_id": tenant_id}},
            {"term": {"thread_id": str(thread_id)}},
            {"term": {"memory_type": memory_type}}
        ]

        query = {"bool": {"filter": filters}}

        try:
            res = await self.client.search(
                index=self.index_name,
                query=query,
                sort=[{"created_at": {"order": "desc"}}],
                size=limit,
            )
            return [{"id": hit["_id"], **hit["_source"]} for hit in res["hits"]["hits"]]

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
        thread_id: Optional[UUID] = None,
        limit: int = 5,
        memory_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        使用全文匹配和租户/线程过滤器进行关键词搜索

        Args:
            tenant_id: 租户ID
            query_text: 搜索查询文本
            thread_id: 对话线程ID
            limit: 返回结果数量限制，默认5
            memory_types: 记忆类型列表

        Returns:
            list[dict]: 搜索结果列表，按创建时间降序排列
        """
        filters = [{"term": {"tenant_id": tenant_id}}]
        if thread_id:
            filters.append({"term": {"thread_id": str(thread_id)}})

        if memory_types:
            filters.append({"terms": {"memory_type": memory_types}})

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
            return [{"id": hit["_id"], **hit["_source"]} for hit in res["hits"]["hits"]]

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
        更新记忆访问元数据

        Args:
            doc_id: 文档ID
            access_count: 访问次数（可选）

        Note:
            始终更新last_accessed_at，如果提供access_count则同时更新
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
        删除所有过期的记忆文档

        删除条件：expires_at < 当前时间

        Note:
            使用delete_by_query批量删除，设置conflicts="proceed"以处理版本冲突
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
