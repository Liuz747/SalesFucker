"""
Hybrid Memory System - Milvus向量数据库适配器

支持高性能向量相似度搜索和记忆检索。
"""
from typing import Any, Optional
from dataclasses import dataclass

from pymilvus import MilvusClient

from libs.factory import infra_registry
from utils import get_component_logger

logger = get_component_logger(__name__)


@dataclass
class SearchResult:
    """
    记忆搜索结果

    将Milvus搜索结果映射为记忆格式。
    """
    memory_id: str
    similarity_score: float
    content: str
    metadata: dict[str, Any]
    created_at: Optional[str] = None
    memory_type: Optional[str] = None


class VectorStore:
    """
    记忆向量存储

    基于Milvus的高性能向量检索引擎，用于hybrid memory系统。
    支持：
    - 向量语义搜索
    - 多租户隔离
    - 批量写入和检索
    - Cosine相似度计算
    """

    def __init__(
        self,
        embedding_dim: int = 3072,
    ):
        """
        初始化记忆向量存储

        Args:
            embedding_dim: 向量维度 (默认3072，text-embedding-3-large)
        """
        self.embedding_dim = embedding_dim
        self._client: Optional[MilvusClient] = None
        logger.info(f"初始化MemoryVectorStore, dim={embedding_dim}")

    @property
    def client(self) -> MilvusClient:
        """获取centralized Milvus client"""
        if self._client is None:
            clients = infra_registry.get_cached_clients()
            if clients.milvus is None:
                raise RuntimeError("Milvus客户端未初始化，请先调用infra_registry.create_clients()")
            self._client = clients.milvus
        return self._client

    def get_collection_name(self, tenant_id: str) -> str:
        """
        生成租户专用集合名称

        Args:
            tenant_id: 租户ID

        Returns:
            str: 集合名称
        """
        return f"memories_{tenant_id}"

    async def create_memory_collection(self, tenant_id: str) -> bool:
        """
        为租户创建记忆集合

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 创建成功返回True
        """
        try:
            collection_name = self.get_collection_name(tenant_id)

            if self.client.has_collection(collection_name):
                logger.debug(f"记忆集合已存在: {collection_name}")
                return True

            # 使用MilvusClient创建集合
            self.client.create_collection(
                collection_name=collection_name,
                dimension=self.embedding_dim,
                metric_type="COSINE",
            )

            logger.info(f"记忆集合创建成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"记忆集合创建失败: {e}")
            return False

    async def insert_memories(
        self,
        tenant_id: str,
        memories: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> bool:
        """
        批量插入记忆向量

        Args:
            tenant_id: 租户ID
            memories: 记忆数据列表，每个记忆包含id, content等字段
            embeddings: 对应的向量嵌入列表

        Returns:
            bool: 插入成功返回True
        """
        if len(memories) != len(embeddings):
            logger.error("记忆数量与向量数量不匹配")
            return False

        try:
            collection_name = self.get_collection_name(tenant_id)

            if not await self.create_memory_collection(tenant_id):
                logger.error(f"租户记忆集合未准备好: {collection_name}")
                return False

            # 准备插入数据
            data = []
            for memory, embedding in zip(memories, embeddings):
                data.append({
                    "id": memory.get("id"),
                    "vector": embedding,
                    "tenant_id": tenant_id,
                    "content": memory.get("content", ""),
                    "metadata": memory.get("metadata", {}),
                    "created_at": memory.get("created_at"),
                    "memory_type": memory.get("memory_type"),
                })

            # 使用MilvusClient插入
            self.client.insert(
                collection_name=collection_name,
                data=data
            )

            logger.info(f"插入{len(memories)}条记忆到租户{tenant_id}")
            return True

        except Exception as e:
            logger.error(f"插入记忆失败: {e}")
            return False

    async def search_similar_memories(
        self,
        tenant_id: str,
        query_embedding: list[float],
        top_k: int = 10,
        score_threshold: float = 0.7,
    ) -> list[SearchResult]:
        """
        语义搜索相似记忆

        基于查询向量检索最相似的k条记忆。

        Args:
            tenant_id: 租户ID
            query_embedding: 查询向量
            top_k: 返回top-k结果
            score_threshold: 相似度阈值 (0.0-1.0)

        Returns:
            List[SearchResult]: 记忆搜索结果列表
        """
        try:
            collection_name = self.get_collection_name(tenant_id)

            # 使用MilvusClient搜索
            results = self.client.search(
                collection_name=collection_name,
                data=[query_embedding],
                limit=top_k,
                filter=f'tenant_id == "{tenant_id}"',
                output_fields=["id", "content", "metadata", "created_at", "memory_type"],
            )

            # 转换为记忆格式
            memory_results = []
            for hits in results:
                for hit in hits:
                    score = hit.get("score")
                    if score is None:
                        score = getattr(hit, "score", None)
                    if score is None:
                        score = hit.get("distance", 0.0)

                    if score < score_threshold:
                        continue

                    entity = hit.get("entity", {})
                    memory_results.append(
                        SearchResult(
                            memory_id=str(hit.get("id", "")),
                            similarity_score=float(score),
                            content=entity.get("content", ""),
                            metadata=entity.get("metadata", {}),
                            created_at=entity.get("created_at"),
                            memory_type=entity.get("memory_type"),
                        )
                    )

            logger.info(
                f"检索到{len(memory_results)}条相似记忆 (tenant={tenant_id})"
            )
            return memory_results

        except Exception as e:
            logger.error(f"记忆搜索失败: {e}")
            return []

    async def delete_memory(self, tenant_id: str, memory_id: str) -> bool:
        """
        删除指定记忆

        Args:
            tenant_id: 租户ID
            memory_id: 记忆ID

        Returns:
            bool: 删除成功返回True
        """
        try:
            collection_name = self.get_collection_name(tenant_id)

            # 使用MilvusClient删除
            self.client.delete(
                collection_name=collection_name,
                filter=f'id == "{memory_id}"'
            )

            logger.info(f"删除记忆成功: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False

    async def get_collection_stats(self, tenant_id: str) -> dict[str, Any]:
        """
        获取记忆集合统计信息

        Args:
            tenant_id: 租户ID

        Returns:
            Dict: 统计信息
        """
        try:
            collection_name = self.get_collection_name(tenant_id)

            # 使用MilvusClient获取统计信息
            stats = self.client.get_collection_stats(collection_name=collection_name)

            result = {
                "collection_name": collection_name,
                "tenant_id": tenant_id,
                "total_entities": stats.get("row_count", 0),
            }

            logger.info(f"获取集合统计: {result}")
            return result

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
