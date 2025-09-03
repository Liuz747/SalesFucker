"""
存储配置模块

包含所有存储相关配置，包括 Elasticsearch、Redis、PostgreSQL 和 Milvus。
"""

from pydantic import Field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings

from .redis_config import RedisConfig

class DatabaseConfig(BaseSettings):
    """
    存储系统配置类
    """
    # PostgreSQL 配置
    DB_HOST: str = Field(
        description="PostgreSQL 服务器主机地址，用于租户管理",
        default="localhost",
    )

    DB_PORT: PositiveInt = Field(
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

    SQLALCHEMY_POOL_SIZE: NonNegativeInt = Field(
        description="PostgreSQL 数据库连接池大小",
        default=10,
    )
    SQLALCHEMY_MAX_OVERFLOW: NonNegativeInt = Field(
        description="PostgreSQL 数据库连接池最大溢出大小",
        default=20,
    )

    SQLALCHEMY_POOL_RECYCLE: NonNegativeInt = Field(
        description="PostgreSQL 数据库连接池回收时间",
        default=3600,
    )

    SQLALCHEMY_POOL_PRE_PING: bool = Field(
        description="PostgreSQL 数据库连接池预 ping",
        default=False,
    )

    SQLALCHEMY_COMMAND_TIMEOUT: NonNegativeInt = Field(
        description="PostgreSQL 数据库命令超时时间",
        default=30,
    )

    SQLALCHEMY_ECHO: bool = Field(
        description="PostgreSQL 数据库是否打印SQL语句",
        default=False,
    )

    # Elasticsearch 配置
    ELASTICSEARCH_URL: str = Field(
        description="Elasticsearch 服务器连接地址，用于存储对话历史和客户记忆",
        default="http://localhost:9200",
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
    
class StorageConfig(
    DatabaseConfig,
    RedisConfig
):
    pass