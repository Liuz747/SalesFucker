"""
长期记忆检索工具

从Elasticsearch中按关键字搜索记忆摘要，支持多租户隔离。
"""

from typing import Any
from uuid import UUID

from core.memory import ElasticsearchIndex
from utils import get_component_logger

logger = get_component_logger(__name__)


async def search_conversation_context(
    tenant_id: str,
    thread_id: UUID,
    query: str,
    limit: int = 5
) -> dict[str, Any]:
    """
    在长期记忆中按关键字搜索摘要

    Args:
        tenant_id: 租户标识符，用于数据隔离
        thread_id: 线程ID，用于限定搜索范围
        query: 搜索查询文本
        limit: 返回结果数量限制，默认5条

    Returns:
        dict: 包含搜索结果的响应字典
            - success: bool, 是否成功
            - results: list[dict], 检索到的记忆列表
            - total_found: int, 找到的记忆总数
            - query: str, 原始查询
    """
    try:
        logger.info(f"开始长期记忆检索 - 租户: {tenant_id}, 查询: {query[:50]}...")

        # 初始化存储管理器
        es_index = ElasticsearchIndex()

        long_term_memories = await es_index.search(
            tenant_id=tenant_id,
            query_text=query,
            thread_id=thread_id,
            limit=limit
        )

        response = {
            "success": True,
            "results": long_term_memories,
            "total_found": len(long_term_memories),
            "query": query
        }

        logger.info(f"长期记忆检索完成 - 找到 {len(long_term_memories)} 条记录")
        return response

    except Exception as e:
        logger.error(f"长期记忆检索失败: {e}")
        return {
            "success": False,
            "results": [],
            "total_found": 0,
            "query": query,
            "error": str(e)
        }