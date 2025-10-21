"""
Hybrid Memory System - Milvus向量数据库适配器

将现有的MilvusDB封装为内存系统专用接口。
支持高性能向量相似度搜索和记忆检索。
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.rag.vector_db import MilvusDB, SearchResult as MilvusSearchResult
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
    metadata: Dict[str, Any]
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
        host: str = "localhost",
        port: int = 19530,
        embedding_dim: int = 3072,
    ):
        """
        初始化记忆向量存储

        Args:
            host: Milvus服务器地址
            port: Milvus端口
            embedding_dim: 向量维度 (默认3072，text-embedding-3-large)
        """
        self.milvus_db = MilvusDB(host=host, port=port)
        self.embedding_dim = embedding_dim
        logger.info(f"初始化MemoryVectorStore: {host}:{port}, dim={embedding_dim}")

    def get_collection_name(self, tenant_id: str) -> str:
        """
        生成租户专用集合名称

        Args:
            tenant_id: 租户ID

        Returns:
            str: 集合名称
        """
        return f"memories_{tenant_id}"

    async def connect(self):
        """连接到Milvus服务"""
        await self.milvus_db.connect()
        logger.info("Milvus连接成功")

    async def create_memory_collection(self, tenant_id: str) -> bool:
        """
        为租户创建记忆集合

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 创建成功返回True
        """
        try:
            collection = await self.milvus_db.create_collection(
                tenant_id=tenant_id, dim=self.embedding_dim
            )
            logger.info(f"记忆集合创建成功: {tenant_id}")
            return collection is not None
        except Exception as e:
            logger.error(f"记忆集合创建失败: {e}")
            return False

    async def insert_memories(
        self,
        tenant_id: str,
        memories: List[Dict[str, Any]],
        embeddings: List[List[float]],
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
            # 复用product插入逻辑，因为底层数据结构相同
            success = await self.milvus_db.insert_products(
                tenant_id=tenant_id, products=memories, embeddings=embeddings
            )

            if success:
                logger.info(f"插入{len(memories)}条记忆到租户{tenant_id}")
            return success

        except Exception as e:
            logger.error(f"插入记忆失败: {e}")
            return False

    async def search_similar_memories(
        self,
        tenant_id: str,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: float = 0.7,
    ) -> List[SearchResult]:
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
            # 使用Milvus搜索
            milvus_results = await self.milvus_db.search_similar(
                tenant_id=tenant_id,
                query_embedding=query_embedding,
                top_k=top_k,
                score_threshold=score_threshold,
            )

            # 转换为记忆格式
            memory_results = []
            for result in milvus_results:
                memory_results.append(
                    SearchResult(
                        memory_id=result.product_id,
                        similarity_score=result.score,
                        content=result.product_data.get("content", ""),
                        metadata=result.product_data.get("metadata", {}),
                        created_at=result.product_data.get("created_at"),
                        memory_type=result.product_data.get("memory_type"),
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
            success = await self.milvus_db.delete_product(
                tenant_id=tenant_id, product_id=memory_id
            )
            if success:
                logger.info(f"删除记忆成功: {memory_id}")
            return success

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False

    async def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取记忆集合统计信息

        Args:
            tenant_id: 租户ID

        Returns:
            Dict: 统计信息
        """
        try:
            stats = await self.milvus_db.get_stats(tenant_id=tenant_id)
            logger.info(f"获取集合统计: {stats}")
            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
