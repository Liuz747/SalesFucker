"""
存储配置模块

包含所有存储相关配置，包括 Elasticsearch、Redis、PostgreSQL 和 Milvus。
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class StorageConfig(BaseSettings):
    """
    存储系统配置类
    """

    # Elasticsearch 配置
    ELASTICSEARCH_URL: str = Field(
        description="Elasticsearch 服务器连接地址，用于存储对话历史和客户记忆",
        default="http://localhost:9200",
    )

    # Redis 配置
    REDIS_URL: str = Field(
        description="Redis 服务器连接地址，用于缓存和会话管理",
        default="redis://localhost:6379",
    )

    # PostgreSQL 配置
    POSTGRES_HOST: str = Field(
        description="PostgreSQL 服务器主机地址，用于租户管理",
        default="localhost",
    )

    POSTGRES_PORT: int = Field(
        description="PostgreSQL 服务器端口号",
        default=5432,
    )

    POSTGRES_DB: str = Field(
        description="PostgreSQL 数据库名称",
        default="mas_tenants",
    )

    POSTGRES_USER: str = Field(
        description="PostgreSQL 数据库用户名",
        default="mas_user",
    )

    POSTGRES_PASSWORD: str = Field(
        description="PostgreSQL 数据库密码",
        default="mas_pass",
    )

    # Milvus 配置
    MILVUS_HOST: str = Field(
        description="Milvus 向量数据库主机地址，用于产品搜索和推荐",
        default="localhost",
    )

    MILVUS_PORT: int = Field(
        description="Milvus 向量数据库端口号",
        default=19530,
    )

    @property
    def postgres_url(self) -> str:
        """构建PostgreSQL连接URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )