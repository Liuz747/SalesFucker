"""
RAG混合检索工具

使用向量+关键词混合搜索检索相关上下文，用于回答问题。
"""

from utils import get_component_logger

logger = get_component_logger(__name__)


async def rag_retrieve(
    tenant_id: str,
    query: str,
    top_k: int = 10
) -> dict:
    pass