"""
索引管理器

该模块提供索引生命周期管理功能。
包括索引创建、更新、删除、版本控制和健康监控。

核心功能:
- 索引创建和删除
- 索引版本管理
- 多租户索引隔离
- 索引健康监控
- 索引统计信息
"""

from typing import Optional

from elasticsearch import AsyncElasticsearch
from pymilvus import MilvusClient

from config.rag_config import rag_config
from infra.ops.milvus_client import get_milvus_connection
from libs.factory import infra_registry
from utils import get_component_logger

logger = get_component_logger(__name__, "IndexManager")


class IndexManager:
    """
    索引管理器

    管理向量数据库和搜索引擎的索引生命周期。
    """

    def __init__(self):
        """初始化IndexManager"""
        self.embedding_dimension = rag_config.EMBEDDING_DIMENSION
        self._milvus_client: Optional[MilvusClient] = None
        self._es_client: Optional[AsyncElasticsearch] = None

    async def _get_milvus_client(self) -> MilvusClient:
        """获取Milvus客户端"""
        if self._milvus_client is None:
            self._milvus_client = await get_milvus_connection()
        return self._milvus_client

    def _get_es_client(self) -> AsyncElasticsearch:
        """获取Elasticsearch客户端"""
        if self._es_client is None:
            self._es_client = infra_registry.get_cached_clients().elasticsearch
        return self._es_client

    # ==================== Milvus集合管理 ====================

    async def create_milvus_collection(
        self,
        collection_name: str,
        description: str = ""
    ) -> bool:
        """
        创建Milvus集合

        参数:
            collection_name: 集合名称
            description: 集合描述

        返回:
            bool: 是否创建成功
        """
        try:
            milvus_client = await self._get_milvus_client()

            # 检查集合是否已存在
            if milvus_client.has_collection(collection_name):
                logger.warning(f"Milvus集合已存在: {collection_name}")
                return False

            # 创建schema
            schema = milvus_client.create_schema(
                auto_id=False,
                enable_dynamic_field=True,
                description=description
            )

            # 添加字段
            schema.add_field(field_name="id", datatype="VARCHAR", max_length=255, is_primary=True)
            schema.add_field(field_name="document_id", datatype="VARCHAR", max_length=255)
            schema.add_field(field_name="tenant_id", datatype="VARCHAR", max_length=64)
            schema.add_field(field_name="content", datatype="VARCHAR", max_length=65535)
            schema.add_field(field_name="embedding", datatype="FLOAT_VECTOR", dim=self.embedding_dimension)

            # 创建索引参数
            index_params = milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128}
            )

            # 创建集合
            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )

            logger.info(f"Milvus集合创建成功: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"创建Milvus集合失败: {collection_name}, 错误: {e}")
            return False

    async def delete_milvus_collection(
        self,
        collection_name: str
    ) -> bool:
        """
        删除Milvus集合

        参数:
            collection_name: 集合名称

        返回:
            bool: 是否删除成功
        """
        try:
            milvus_client = await self._get_milvus_client()

            if not milvus_client.has_collection(collection_name):
                logger.warning(f"Milvus集合不存在: {collection_name}")
                return False

            milvus_client.drop_collection(collection_name)
            logger.info(f"Milvus集合删除成功: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"删除Milvus集合失败: {collection_name}, 错误: {e}")
            return False

    async def get_milvus_collection_stats(
        self,
        collection_name: str
    ) -> Optional[dict]:
        """
        获取Milvus集合统计信息

        参数:
            collection_name: 集合名称

        返回:
            Optional[dict]: 统计信息
        """
        try:
            milvus_client = await self._get_milvus_client()

            if not milvus_client.has_collection(collection_name):
                logger.warning(f"Milvus集合不存在: {collection_name}")
                return None

            stats = milvus_client.get_collection_stats(collection_name)

            return {
                "collection_name": collection_name,
                "row_count": stats.get("row_count", 0),
                "data_size": stats.get("data_size", 0)
            }

        except Exception as e:
            logger.error(f"获取Milvus集合统计失败: {collection_name}, 错误: {e}")
            return None

    async def list_milvus_collections(self) -> list[str]:
        """
        列出所有Milvus集合

        返回:
            list[str]: 集合名称列表
        """
        try:
            milvus_client = await self._get_milvus_client()
            collections = milvus_client.list_collections()
            return collections

        except Exception as e:
            logger.error(f"列出Milvus集合失败: {e}")
            return []

    # ==================== Elasticsearch索引管理 ====================

    async def create_es_index(
        self,
        index_name: str,
        use_ik_analyzer: bool = True
    ) -> bool:
        """
        创建Elasticsearch索引

        参数:
            index_name: 索引名称
            use_ik_analyzer: 是否使用IK中文分词器

        返回:
            bool: 是否创建成功
        """
        try:
            es_client = self._get_es_client()

            # 检查索引是否已存在
            if await es_client.indices.exists(index=index_name):
                logger.warning(f"Elasticsearch索引已存在: {index_name}")
                return False

            # 创建索引映射
            content_analyzer = "ik_max_word" if use_ik_analyzer else "standard"
            search_analyzer = "ik_smart" if use_ik_analyzer else "standard"

            mappings = {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": content_analyzer,
                        "search_analyzer": search_analyzer
                    },
                    "token_count": {"type": "integer"},
                    "metadata": {"type": "object", "enabled": True},
                    "created_at": {"type": "date"}
                }
            }

            # 创建索引
            await es_client.indices.create(
                index=index_name,
                mappings=mappings
            )

            logger.info(f"Elasticsearch索引创建成功: {index_name}")
            return True

        except Exception as e:
            logger.error(f"创建Elasticsearch索引失败: {index_name}, 错误: {e}")
            return False

    async def delete_es_index(
        self,
        index_name: str
    ) -> bool:
        """
        删除Elasticsearch索引

        参数:
            index_name: 索引名称

        返回:
            bool: 是否删除成功
        """
        try:
            es_client = self._get_es_client()

            if not await es_client.indices.exists(index=index_name):
                logger.warning(f"Elasticsearch索引不存在: {index_name}")
                return False

            await es_client.indices.delete(index=index_name)
            logger.info(f"Elasticsearch索引删除成功: {index_name}")
            return True

        except Exception as e:
            logger.error(f"删除Elasticsearch索引失败: {index_name}, 错误: {e}")
            return False

    async def get_es_index_stats(
        self,
        index_name: str
    ) -> Optional[dict]:
        """
        获取Elasticsearch索引统计信息

        参数:
            index_name: 索引名称

        返回:
            Optional[dict]: 统计信息
        """
        try:
            es_client = self._get_es_client()

            if not await es_client.indices.exists(index=index_name):
                logger.warning(f"Elasticsearch索引不存在: {index_name}")
                return None

            stats = await es_client.indices.stats(index=index_name)
            index_stats = stats["indices"][index_name]["total"]

            return {
                "index_name": index_name,
                "document_count": index_stats["docs"]["count"],
                "store_size_bytes": index_stats["store"]["size_in_bytes"],
                "store_size_mb": round(index_stats["store"]["size_in_bytes"] / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"获取Elasticsearch索引统计失败: {index_name}, 错误: {e}")
            return None

    async def list_es_indices(self) -> list[str]:
        """
        列出所有Elasticsearch索引

        返回:
            list[str]: 索引名称列表
        """
        try:
            es_client = self._get_es_client()
            indices = await es_client.cat.indices(format="json")
            return [idx["index"] for idx in indices]

        except Exception as e:
            logger.error(f"列出Elasticsearch索引失败: {e}")
            return []

    # ==================== 统一管理接口 ====================

    async def create_index_pair(
        self,
        name: str,
        description: str = ""
    ) -> dict[str, bool]:
        """
        创建索引对（Milvus集合 + Elasticsearch索引）

        参数:
            name: 索引名称
            description: 描述

        返回:
            dict[str, bool]: 创建结果
        """
        results = {
            "milvus": await self.create_milvus_collection(name, description),
            "elasticsearch": await self.create_es_index(name)
        }

        if all(results.values()):
            logger.info(f"索引对创建成功: {name}")
        else:
            logger.warning(f"索引对创建部分失败: {name}, 结果: {results}")

        return results

    async def delete_index_pair(
        self,
        name: str
    ) -> dict[str, bool]:
        """
        删除索引对（Milvus集合 + Elasticsearch索引）

        参数:
            name: 索引名称

        返回:
            dict[str, bool]: 删除结果
        """
        results = {
            "milvus": await self.delete_milvus_collection(name),
            "elasticsearch": await self.delete_es_index(name)
        }

        if all(results.values()):
            logger.info(f"索引对删除成功: {name}")
        else:
            logger.warning(f"索引对删除部分失败: {name}, 结果: {results}")

        return results

    async def get_index_stats(
        self,
        name: str
    ) -> dict:
        """
        获取索引统计信息

        参数:
            name: 索引名称

        返回:
            dict: 统计信息
        """
        milvus_stats = await self.get_milvus_collection_stats(name)
        es_stats = await self.get_es_index_stats(name)

        return {
            "index_name": name,
            "milvus": milvus_stats,
            "elasticsearch": es_stats
        }

    async def health_check(self) -> dict:
        """
        健康检查

        返回:
            dict: 健康状态
        """
        try:
            # 检查Milvus
            milvus_client = await self._get_milvus_client()
            milvus_collections = milvus_client.list_collections()
            milvus_healthy = True
        except Exception as e:
            logger.error(f"Milvus健康检查失败: {e}")
            milvus_healthy = False
            milvus_collections = []

        try:
            # 检查Elasticsearch
            es_client = self._get_es_client()
            es_health = await es_client.cluster.health()
            es_healthy = es_health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Elasticsearch健康检查失败: {e}")
            es_healthy = False
            es_health = {}

        return {
            "milvus": {
                "healthy": milvus_healthy,
                "collections_count": len(milvus_collections)
            },
            "elasticsearch": {
                "healthy": es_healthy,
                "status": es_health.get("status", "unknown"),
                "number_of_nodes": es_health.get("number_of_nodes", 0)
            }
        }


# 全局IndexManager实例
index_manager = IndexManager()
