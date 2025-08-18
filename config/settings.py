"""
Application Configuration Settings

This module handles all configuration management for the MAS system.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings."""

    # Application
    app_name: str = "MAS Cosmetic Agent System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # Database Configuration
    elasticsearch_url: str = Field(default="http://localhost:9200", env="ELASTICSEARCH_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # PostgreSQL Configuration (for tenant management)
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="mas_tenants", env="POSTGRES_DB")
    postgres_user: str = Field(default="mas_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="mas_pass", env="POSTGRES_PASSWORD")

    @property
    def postgres_url(self) -> str:
        """构建PostgreSQL连接URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # LLM Provider API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    deepseek_api_key: str = Field(default="", env="DEEPSEEK_API_KEY")

    # Milvus Configuration
    milvus_host: str = Field(default="localhost", env="MILVUS_HOST")
    milvus_port: int = Field(default=19530, env="MILVUS_PORT")

    # Application Configuration
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    app_env: str = Field(default="development", env="APP_ENV")

    # Multi-LLM Configuration
    default_llm_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    fallback_llm_provider: str = Field(default="anthropic", env="FALLBACK_LLM_PROVIDER")
    enable_cost_tracking: bool = Field(default=True, env="ENABLE_COST_TRACKING")
    enable_intelligent_routing: bool = Field(default=True, env="ENABLE_INTELLIGENT_ROUTING")

    # Multi-Tenant Configuration
    default_tenant_id: str = Field(default="cosmetic_brand_1", env="DEFAULT_TENANT_ID")

    # 是否启用JWKS验证（默认关闭，原型阶段仅PEM）
    enable_jwks: bool = Field(default=False, env="ENABLE_JWKS")

    # Service Authentication (Backend → MAS)
    app_key: Optional[str] = Field(default="123", env="APP_KEY")
    app_jwt_issuer: str = Field(default="mas-ai-service", env="APP_JWT_ISSUER")
    app_jwt_audience: str = Field(default="ai-admin", env="APP_JWT_AUDIENCE")
    app_token_ttl: int = Field(default=3600, env="APP_TOKEN_TTL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/mas.log", env="LOG_FILE")

    # Performance
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
