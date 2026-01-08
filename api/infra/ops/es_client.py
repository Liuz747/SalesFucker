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
        logger.error(f"✗ Elasticsearch 客户端创建失败: {e}")
        raise


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
        return await client.ping(error_trace=False)
    except Exception as e:
        logger.error(f"✗ Elasticsearch连接测试失败: {e}")
        return False


async def create_memory_index(client: AsyncElasticsearch, force_recreate: bool = False) -> bool:
    """
    创建memory_v1索引

    索引特性：
    - dense_vector字段仅支持向量存储
    - text字段支持全文检索
    - 多租户隔离字段
    - 时间戳和TTL支持

    Args:
        client: 异步ES客户端实例
        force_recreate: 是否强制重建索引（会删除现有数据）

    Returns:
        bool: 创建成功返回True
    """
    try:
        # 检查索引是否已存在
        exists = await client.indices.exists(index=mas_config.ES_MEMORY_INDEX)

        if exists:
            if force_recreate:
                logger.warning(f"删除现有索引: {mas_config.ES_MEMORY_INDEX}")
                await client.indices.delete(index=mas_config.ES_MEMORY_INDEX)
            else:
                logger.info(f"索引已存在: {mas_config.ES_MEMORY_INDEX}")
                return True

        # 定义索引映射
        index_mapping = {
            "settings": {
                "number_of_shards": mas_config.ES_NUMBER_OF_SHARDS,
                "number_of_replicas": 0,
                "refresh_interval": mas_config.ES_REFRESH_INTERVAL,
                "index": {
                    "max_result_window": 10000,  # 最大分页深度
                },
                "analysis": {
                    "analyzer": {
                        "ik_max": {"type": "ik_max_word"},
                        "ik_smart": {"type": "ik_smart"}
                    }
                }
            },
            "mappings": {
                "dynamic": False,
                "properties": {
                    # 核心字段
                    "tenant_id": {"type": "keyword"},
                    "thread_id": {"type": "keyword",},
                    # 记忆内容
                    "content": {
                        "type": "text",
                        "analyzer": "ik_max",
                        "search_analyzer": "ik_smart",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    # 向量嵌入 - 关键字段
                    "embedding": {
                        "type": "dense_vector",
                        "dims": mas_config.ES_VECTOR_DIMENSION,
                        "index": False
                    },
                    # 元数据
                    "memory_type": {"type": "keyword"},  # short_term, long_term, episodic, semantic
                    "importance_score": {"type": "float", "doc_values": False},  # 0.0-1.0
                    "access_count": {"type": "integer", "doc_values": False},
                    "last_accessed_at": {"type": "date"},
                    "created_at": {"type": "date"},
                    "expires_at": {"type": "date"},
                    # 关联信息
                    "tags": {"type": "keyword"},
                    "entities": {
                        "type": "object",
                        "enabled": True,
                    },
                    # 检索元数据
                    "metadata": {
                        "type": "object",
                        "enabled": False,  # 不索引，仅存储
                    },
                }
            }
        }

        # 创建索引
        response = await client.indices.create(index=mas_config.ES_MEMORY_INDEX, **index_mapping)

        # wait cluster ready
        await client.cluster.health(index=mas_config.ES_MEMORY_INDEX, wait_for_status="yellow")


        logger.info(f"索引创建成功: {mas_config.ES_MEMORY_INDEX} - {response}")
        return True

    except Exception as e:
        logger.error(f"索引创建失败: {e}")
        return False
