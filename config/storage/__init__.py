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
    DB_HOST: str = Field(
        description="PostgreSQL 服务器主机地址，用于租户管理",
        default="localhost",
    )

    DB_PORT: int = Field(
        description="PostgreSQL 服务器端口号",
        default=5432,
    )

    DB_NAME: str = Field(
        description="PostgreSQL 数据库名称",
        default="mas",
    )

    POSTGRES_USER: str = Field(
        description="PostgreSQL 数据库用户名",
        default="postgres",
    )

    POSTGRES_PWD: str = Field(
        description="PostgreSQL 数据库密码",
        default=None,
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
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PWD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )