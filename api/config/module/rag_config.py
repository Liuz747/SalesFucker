"""
RAG系统配置

该模块定义RAG（检索增强生成）系统的所有配置参数。
包括embedding生成、文档分块、检索策略等配置。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class RAGConfig(BaseSettings):
    """RAG系统配置"""

    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="Embedding模型名称"
    )

    EMBEDDING_DIMENSION: int = Field(
        default=3072,
        description="Embedding向量维度"
    )

    EMBEDDING_CACHE_TTL: int = Field(
        default=604800,  # 7天
        description="Embedding缓存过期时间（秒）"
    )

    EMBEDDING_BATCH_SIZE: int = Field(
        default=100,
        description="批量生成embedding的最大数量"
    )

    CHUNK_SIZE: int = Field(
        default=512,
        description="文档分块大小（tokens）"
    )

    CHUNK_OVERLAP: float = Field(
        default=0.1,
        description="分块重叠比例（0-1）"
    )

    MIN_CHUNK_SIZE: int = Field(
        default=50,
        description="最小分块大小（tokens）"
    )

    MAX_CHUNK_SIZE: int = Field(
        default=1000,
        description="最大分块大小（tokens）"
    )

    DEFAULT_TOP_K: int = Field(
        default=5,
        description="默认返回的检索结果数量"
    )

    MIN_SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        description="最小相似度阈值（0-1）"
    )

    RETRIEVAL_CACHE_TTL: int = Field(
        default=300,  # 5分钟
        description="检索结果缓存过期时间（秒）"
    )

    VECTOR_SEARCH_WEIGHT: float = Field(
        default=0.7,
        description="向量搜索权重（0-1）"
    )

    KEYWORD_SEARCH_WEIGHT: float = Field(
        default=0.3,
        description="关键词搜索权重（0-1）"
    )
