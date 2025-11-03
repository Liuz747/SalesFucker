"""
Elasticsearch客户端工厂

提供异步ES客户端连接管理。
"""

from elasticsearch import AsyncElasticsearch

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)


async def get_es_client() -> AsyncElasticsearch:
    """
    异步获取Elasticsearch客户端

    使用全局单例模式，支持连接复用。

    Returns:
        AsyncElasticsearch: 异步ES客户端实例
    """
    try: 
        logger.info(f"初始化Elasticsearch连接: {mas_config.ELASTIC_HOST}")
        client_options = {
            "hosts": [mas_config.elasticsearch_url],
            "max_retries": mas_config.ES_MAX_RETRIES,
            "retry_on_timeout": True,
            "request_timeout": mas_config.ES_REQUEST_TIMEOUT,
        }

        if mas_config.ELASTIC_PASSWORD:
            client_options["basic_auth"] = (
                mas_config.ELASTIC_USER,
                mas_config.ELASTIC_PASSWORD,
            )
        else:
            logger.warning("Elasticsearch认证配置不完整，已跳过basic_auth设置")

        es_client = AsyncElasticsearch(**client_options)

        return es_client
    except Exception as e:
        logger.error(f"✗ Elasticsearch连接失败: {e}")
        raise ConnectionError(f"Failed to connect to Elasticsearch: {e}")


async def close_es_client(client: AsyncElasticsearch):
    """
    关闭Elasticsearch客户端连接
    """
    try:
        await client.close()
        logger.info("Elasticsearch连接关闭成功")
    except Exception as e:
        logger.error(f"Elasticsearch连接关闭失败: {e}")


async def verify_es_connection(client: AsyncElasticsearch) -> bool:
    """
    验证Elasticsearch连接

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        return await client.ping()
    except Exception as e:
        logger.error(f"✗ Elasticsearch连接测试失败: {e}")
        return False
