"""
Hybrid Memory System - Elasticsearch索引管理

创建和管理memory_v1索引，支持：
- 密集向量存储和kNN搜索
- 全文检索和语义搜索
- 多租户数据隔离
- 时间范围查询和TTL管理
"""
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch

from config import mas_config
from libs.factory import infra_registry
from utils import get_component_logger, to_isoformat

logger = get_component_logger(__name__)


class IndexManager:
    """
    Memory索引管理器

    负责memory_v1索引的创建、更新和维护。
    支持向量检索、全文搜索和混合查询。
    """

    def __init__(self):
        self._es_client: Optional[AsyncElasticsearch] = None
        self.index_name = mas_config.ES_MEMORY_INDEX
        self.vector_dim = mas_config.ES_VECTOR_DIMENSION

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
                    "number_of_replicas": mas_config.ES_NUMBER_OF_REPLICAS,
                    "refresh_interval": mas_config.ES_REFRESH_INTERVAL,
                    "index": {
                        "max_result_window": 10000,  # 最大分页深度
                    },
                },
                "mappings": {
                    "properties": {
                        # 核心字段
                        "memory_id": {
                            "type": "keyword",
                        },
                        "tenant_id": {
                            "type": "keyword",
                        },
                        "thread_id": {
                            "type": "keyword",
                        },
                        "user_id": {
                            "type": "keyword",
                        },
                        # 记忆内容
                        "content": {
                            "type": "text",
                            "analyzer": "standard",  # 使用标准分词器，支持中英文
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256,
                                }
                            },
                        },
                        "summary": {
                            "type": "text",
                            "analyzer": "standard",
                        },
                        # 向量嵌入 - 关键字段
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.vector_dim,
                            "index": True,
                            "similarity": mas_config.ES_SIMILARITY_METRIC,
                        },
                        # 元数据
                        "memory_type": {
                            "type": "keyword",  # short_term, long_term, episodic, semantic
                        },
                        "importance_score": {
                            "type": "float",  # 0.0-1.0
                        },
                        "access_count": {
                            "type": "integer",
                        },
                        "last_accessed_at": {
                            "type": "date",
                        },
                        "created_at": {
                            "type": "date",
                        },
                        "expires_at": {
                            "type": "date",  # 用于TTL删除
                        },
                        # 关联信息
                        "tags": {
                            "type": "keyword",
                        },
                        "entities": {
                            "type": "object",
                            "enabled": True,
                        },
                        # 上下文信息
                        "context": {
                            "type": "object",
                            "properties": {
                                "conversation_id": {"type": "keyword"},
                                "message_id": {"type": "keyword"},
                                "agent_name": {"type": "keyword"},
                                "intent": {"type": "keyword"},
                                "sentiment": {"type": "keyword"},
                            },
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
            response = await self.client.indices.create(
                index=self.index_name, body=index_mapping
            )

            logger.info(f"索引创建成功: {self.index_name} - {response}")
            return True

        except Exception as e:
            logger.error(f"索引创建失败: {e}")
            return False

    async def get_index_info(self) -> Optional[dict[str, Any]]:
        """
        获取索引信息

        Returns:
            dict: 索引统计信息，失败返回None
        """
        try:
            # 检查索引是否存在
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                logger.warning(f"索引不存在: {self.index_name}")
                return None

            # 获取索引统计
            stats = await self.client.indices.stats(index=self.index_name)

            # 获取索引映射
            mappings = await self.client.indices.get_mapping(
                index=self.index_name
            )

            return {
                "index_name": self.index_name,
                "docs_count": stats["_all"]["primaries"]["docs"]["count"],
                "store_size": stats["_all"]["primaries"]["store"]["size_in_bytes"],
                "mappings": mappings[self.index_name]["mappings"],
                "created": True,
            }

        except Exception as e:
            logger.error(f"获取索引信息失败: {e}")
            return None

    async def refresh_index(self) -> bool:
        """
        刷新索引，使新文档立即可搜索

        Returns:
            bool: 刷新成功返回True
        """
        try:
            await self.client.indices.refresh(index=self.index_name)
            logger.info(f"索引刷新成功: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"索引刷新失败: {e}")
            return False

    async def delete_expired_memories(self, batch_size: int = 1000) -> int:
        """
        删除过期记忆

        基于expires_at字段删除过期数据。

        Args:
            batch_size: 批量删除大小

        Returns:
            int: 删除的记录数
        """
        try:
            now = to_isoformat()

            query = {
                "query": {
                    "range": {
                        "expires_at": {
                            "lt": now,
                        }
                    }
                }
            }

            response = await self.client.delete_by_query(
                index=self.index_name,
                body=query,
                conflicts="proceed",
                wait_for_completion=True,
                scroll_size=batch_size,
            )

            deleted_count = response.get("deleted", 0)
            logger.info(f"删除过期记忆: {deleted_count}条")
            return deleted_count

        except Exception as e:
            logger.error(f"删除过期记忆失败: {e}")
            return 0

    async def update_index_settings(
        self, settings: dict[str, Any]
    ) -> bool:
        """
        更新索引设置

        Args:
            settings: 要更新的设置字典

        Returns:
            bool: 更新成功返回True
        """
        try:
            await self.client.indices.put_settings(
                index=self.index_name, body=settings
            )
            logger.info(f"索引设置更新成功: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"索引设置更新失败: {e}")
            return False
