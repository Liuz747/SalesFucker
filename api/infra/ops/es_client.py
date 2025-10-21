"""
Elasticsearch客户端工厂

提供异步ES客户端连接管理。
"""
from typing import Optional

from elasticsearch import AsyncElasticsearch

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)

_es_client: Optional[AsyncElasticsearch] = None


async def get_es_client() -> AsyncElasticsearch:
    """
    异步获取Elasticsearch客户端

    使用全局单例模式，支持连接复用。

    Returns:
        AsyncElasticsearch: 异步ES客户端实例
    """
    global _es_client

    if _es_client is None:
        logger.info(f"初始化Elasticsearch连接: {mas_config.ELASTICSEARCH_URL}")
        client_options = {
            "hosts": mas_config.ELASTICSEARCH_URL,
            "verify_certs": mas_config.ELASTICSEARCH_VERIFY_CERTS,
            "max_retries": mas_config.ES_MAX_RETRIES,
            "retry_on_timeout": True,
            "request_timeout": mas_config.ES_REQUEST_TIMEOUT,
        }

        if mas_config.ELASTICSEARCH_USER and mas_config.ELASTICSEARCH_PASSWORD:
            client_options["basic_auth"] = (
                mas_config.ELASTICSEARCH_USER,
                mas_config.ELASTICSEARCH_PASSWORD,
            )
        elif mas_config.ELASTICSEARCH_USER or mas_config.ELASTICSEARCH_PASSWORD:
            logger.warning("Elasticsearch认证配置不完整，已跳过basic_auth设置")

        _es_client = AsyncElasticsearch(**client_options)
        logger.info("Elasticsearch客户端初始化完成")

    return _es_client


async def close_es_client():
    """
    关闭Elasticsearch客户端连接

    优雅关闭连接，释放资源。
    """
    global _es_client

    if _es_client:
        await _es_client.close()
        _es_client = None
        logger.info("Elasticsearch连接关闭成功")


async def verify_es_connection() -> bool:
    """
    验证Elasticsearch连接

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        es_client = await get_es_client()
        info = await es_client.info()
        version = info.get('version', {}).get('number', 'unknown')
        logger.info(f"Elasticsearch连接测试成功 - 版本: {version}")
        return True
    except Exception as e:
        logger.error(f"Elasticsearch连接测试失败: {e}")
        return False
