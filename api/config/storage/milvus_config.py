"""
Milvus向量数据库配置
"""
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class MilvusConfig(BaseSettings):
    """
    Milvus配置
    """
    MILVUS_HOST: str = Field(
        description="Milvus向量数据库主机地址",
        default="localhost",
    )

    MILVUS_PORT: PositiveInt = Field(
        description="Milvus向量数据库端口号",
        default=19530,
    )

    MILVUS_INDEX_TYPE: str = Field(
        description="Milvus索引类型 (IVF_FLAT, IVF_SQ8, HNSW)",
        default="IVF_FLAT",
    )

    MILVUS_METRIC_TYPE: str = Field(
        description="相似度度量方式 (COSINE, L2, IP)",
        default="COSINE",
    )

    MILVUS_NLIST: PositiveInt = Field(
        description="IVF索引的聚类中心数",
        default=128,
    )

    MILVUS_NPROBE: PositiveInt = Field(
        description="搜索时检查的聚类数",
        default=10,
    )

    @property
    def milvus_uri(self) -> str:
        """获取Milvus连接URL"""
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"
