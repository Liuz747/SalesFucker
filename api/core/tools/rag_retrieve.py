"""
RAG混合检索工具

使用向量+关键词混合搜索检索相关上下文，用于回答问题。
"""

from core.rag.search import ProductSearch, SearchQuery
from utils import get_component_logger

logger = get_component_logger(__name__)


async def rag_retrieve(
    tenant_id: str,
    query: str,
    top_k: int = 10
) -> dict:
    """
    使用混合搜索检索相关上下文

    结合向量语义搜索和关键词匹配，为问答提供最相关的上下文信息。

    Args:
        tenant_id: 租户标识符
        query: 自然语言问题或查询
        top_k: 返回的上下文文档数量

    Returns:
        dict: 包含检索结果的响应字典
            - success: bool, 是否成功
            - contexts: list[dict], 检索到的上下文列表
            - total_found: int, 找到的上下文总数
            - query: str, 原始查询
    """
    try:
        logger.info(f"开始RAG混合检索 - 租户: {tenant_id}, 查询: {query[:50]}...")

        # 初始化产品搜索引擎
        product_search = ProductSearch()

        # 确保初始化完成
        if not await product_search.initialize():
            logger.error("ProductSearch初始化失败")
            return {
                "success": False,
                "contexts": [],
                "total_found": 0,
                "query": query,
                "error": "搜索引擎初始化失败"
            }

        # 构建搜索查询
        search_query = SearchQuery(
            text=query,
            tenant_id=tenant_id,
            top_k=top_k,
            min_score=0.6  # RAG检索使用较低的阈值以获取更多候选
        )

        # 执行混合搜索
        search_response = await product_search.search(search_query)

        # 转换为上下文格式
        contexts = []
        for result in search_response.results:
            context_dict = {
                "product_id": result.product_id,
                "content": result.product_data,
                "relevance_score": result.score,
                "source": "product_database",
                "retrieved_at": "current_timestamp"  # 在实际实现中应使用真实时间戳
            }
            contexts.append(context_dict)

        response = {
            "success": True,
            "contexts": contexts,
            "total_found": len(contexts),
            "query": query,
            "cache_hit": search_response.cache_hit,
            "query_embedding": search_response.query_embedding
        }

        logger.info(f"RAG混合检索完成 - 找到 {len(contexts)} 个上下文")
        return response

    except Exception as e:
        logger.error(f"RAG混合检索失败: {e}")
        return {
            "success": False,
            "contexts": [],
            "total_found": 0,
            "query": query,
            "error": str(e)
        }