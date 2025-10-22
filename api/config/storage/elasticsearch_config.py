"""
Hybrid Memory System - Elasticsearch配置扩展

为hybrid memory系统添加ES特定配置，包括索引设置、向量维度等。
"""

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class ElasticsearchConfig(BaseSettings):
    """
    Elasticsearch记忆系统配置

    用于hybrid memory的中长期存储配置。
    """

    # Elasticsearch 配置
    ELASTICSEARCH_URL: str = Field(
        description="Elasticsearch 服务器连接地址，用于存储对话历史和客户记忆",
        default="http://localhost:9200",
    )

    ELASTIC_USER: str | None = Field(
        description="Elasticsearch 用户名（自托管部署需要认证）",
        default="elastic",
    )

    ELASTIC_PASSWORD: str | None = Field(
        description="Elasticsearch 密码（自托管部署需要认证）",
        default="changeme",
    )

    ES_MEMORY_INDEX: str = Field(
        description="Hybrid memory主索引名称",
        default="memory_v1",
    )

    ES_VECTOR_DIMENSION: PositiveInt = Field(
        description="向量嵌入维度 (text-embedding-3-large使用3072)",
        default=3072,
    )

    ES_SIMILARITY_METRIC: str = Field(
        description="向量相似度计算方式 (cosine/dot_product/l2_norm)",
        default="cosine",
    )

    ES_NUM_CANDIDATES: PositiveInt = Field(
        description="kNN搜索候选数量",
        default=100,
    )

    ES_MEMORY_TTL_DAYS: PositiveInt = Field(
        description="记忆数据保留天数 (用于ILM策略)",
        default=365,
    )

    ES_REFRESH_INTERVAL: str = Field(
        description="索引刷新间隔 (实时性要求)",
        default="1s",
    )

    ES_NUMBER_OF_SHARDS: PositiveInt = Field(
        description="索引分片数量",
        default=3,
    )

    ES_NUMBER_OF_REPLICAS: PositiveInt = Field(
        description="索引副本数量",
        default=1,
    )

    # 记忆检索配置
    ES_MEMORY_SEARCH_LIMIT: PositiveInt = Field(
        description="单次检索返回的最大记忆数量",
        default=20,
    )

    ES_MEMORY_SCORE_THRESHOLD: float = Field(
        description="记忆相关性阈值 (0.0-1.0)",
        default=0.7,
        ge=0.0,
        le=1.0,
    )

    ES_MAX_RETRIES: PositiveInt = Field(
        description="操作失败最大重试次数",
        default=3,
    )

    ES_REQUEST_TIMEOUT: PositiveInt = Field(
        description="请求超时时间(秒)",
        default=30,
    )
