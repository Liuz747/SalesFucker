"""
长期记忆检索工具

从向量数据库中检索语义相似的文档或记忆，支持多租户隔离。
"""

from core.memory.vector_store import VectorStore, SearchResult
from core.rag.embedding import EmbeddingGenerator
from utils import get_component_logger

logger = get_component_logger(__name__)


async def search_context(
    tenant_id: str,
    query: str,
    top_k: int = 10
) -> dict:
    """
    检索语义相似的长期记忆

    使用语义搜索从向量数据库中查找与查询最相关的记忆。

    Args:
        tenant_id: 租户标识符，用于多租户隔离
        query: 用户查询或嵌入文本
        top_k: 返回的相似记忆数量

    Returns:
        dict: 包含搜索结果的响应字典
            - success: bool, 是否成功
            - memories: list[dict], 检索到的记忆列表
            - total_found: int, 找到的记忆总数
            - query: str, 原始查询
    """
    try:
        logger.info(f"开始长期记忆检索 - 租户: {tenant_id}, 查询: {query[:50]}...")

        # 初始化组件
        embedding_generator = EmbeddingGenerator()
        vector_store = VectorStore()

        # 生成查询向量
        embedding_result = await embedding_generator.generate(query)
        query_embedding = embedding_result.embedding

        # 执行向量搜索
        search_results: list[SearchResult] = await vector_store.search_similar_memories(
            tenant_id=tenant_id,
            query_embedding=query_embedding,
            top_k=top_k,
            score_threshold=0.7  # 默认相似度阈值
        )

        # 转换为工具响应格式
        memories = []
        for result in search_results:
            memory_dict = {
                "memory_id": result.memory_id,
                "content": result.content,
                "similarity_score": result.similarity_score,
                "metadata": result.metadata,
                "created_at": result.created_at,
                "memory_type": result.memory_type
            }
            memories.append(memory_dict)

        response = {
            "success": True,
            "memories": memories,
            "total_found": len(memories),
            "query": query,
            "cache_hit": embedding_result.cache_hit
        }

        logger.info(f"长期记忆检索完成 - 找到 {len(memories)} 条记忆")
        return response

    except Exception as e:
        logger.error(f"长期记忆检索失败: {e}")
        return {
            "success": False,
            "memories": [],
            "total_found": 0,
            "query": query,
            "error": str(e)
        }