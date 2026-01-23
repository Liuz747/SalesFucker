"""
RAG混合检索工具

使用向量+关键词混合搜索检索相关上下文，用于回答问题。
支持从文档知识库、产品目录等多种来源检索信息。
"""

from typing import Any, Optional

from core.rag import retrieval_service
from utils import get_component_logger

logger = get_component_logger(__name__)


async def rag_retrieve(
    tenant_id: str,
    query: str,
    retrieval_type: str = "documents",
    top_k: int = 5,
    search_strategy: str = "hybrid",
    filters: Optional[dict] = None
) -> dict[str, Any]:
    """
    RAG检索工具 - 从知识库检索相关信息

    Args:
        tenant_id: 租户标识符，用于数据隔离
        query: 检索查询文本
        retrieval_type: 检索类型 (documents, products, conversations)
        top_k: 返回结果数量限制，默认5条
        search_strategy: 搜索策略 (vector, keyword, hybrid)
        filters: 额外的过滤条件（可选）

    Returns:
        dict: 包含检索结果的响应字典
            - success: bool, 是否成功
            - results: list[dict], 检索到的内容列表
            - total_found: int, 找到的结果总数
            - query: str, 原始查询
            - strategy: str, 使用的搜索策略
    """
    try:
        logger.info(f"开始RAG检索 - 租户: {tenant_id}, 查询: {query[:50]}..., 策略: {search_strategy}")

        # 根据检索类型确定集合/索引名称
        collection_name = _get_collection_name(retrieval_type)
        index_name = _get_index_name(retrieval_type)

        # 根据搜索策略执行检索
        if search_strategy == "vector":
            results = await retrieval_service.vector_search(
                tenant_id=tenant_id,
                query=query,
                collection_name=collection_name,
                top_k=top_k
            )
        elif search_strategy == "keyword":
            results = await retrieval_service.keyword_search(
                tenant_id=tenant_id,
                query=query,
                index_name=index_name,
                top_k=top_k
            )
        else:  # hybrid (default)
            results = await retrieval_service.hybrid_search(
                tenant_id=tenant_id,
                query=query,
                collection_name=collection_name,
                index_name=index_name,
                top_k=top_k
            )

        # 格式化结果
        formatted_results = [
            {
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
                "source": result.source
            }
            for result in results
        ]

        response = {
            "success": True,
            "results": formatted_results,
            "total_found": len(formatted_results),
            "query": query,
            "strategy": search_strategy,
            "retrieval_type": retrieval_type
        }

        logger.info(f"RAG检索完成 - 找到 {len(formatted_results)} 条结果")
        return response

    except Exception as e:
        logger.error(f"RAG检索失败: {e}")
        return {
            "success": False,
            "results": [],
            "total_found": 0,
            "query": query,
            "strategy": search_strategy,
            "retrieval_type": retrieval_type,
            "error": str(e)
        }


def _get_collection_name(retrieval_type: str) -> str:
    """
    根据检索类型获取Milvus集合名称

    Args:
        retrieval_type: 检索类型

    Returns:
        str: 集合名称
    """
    mapping = {
        "documents": "documents",
        "products": "products",
        "conversations": "conversations",
        "faqs": "faqs"
    }
    return mapping.get(retrieval_type, "documents")


def _get_index_name(retrieval_type: str) -> str:
    """
    根据检索类型获取Elasticsearch索引名称

    Args:
        retrieval_type: 检索类型

    Returns:
        str: 索引名称
    """
    mapping = {
        "documents": "documents",
        "products": "products",
        "conversations": "memory_v1",
        "faqs": "faqs"
    }
    return mapping.get(retrieval_type, "documents")