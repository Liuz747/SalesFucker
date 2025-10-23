"""
Milvus客户端工厂

提供Milvus向量数据库连接管理。
"""

from pymilvus import MilvusClient, MilvusException

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)


async def get_milvus_connection() -> MilvusClient:
    """
    获取Milvus客户端

    使用单例模式管理客户端实例。

    Returns:
        MilvusClient: Milvus客户端实例
    """
    try:
        logger.info(f"初始化Milvus客户端: {mas_config.MILVUS_HOST}")
        client = MilvusClient(
            uri=mas_config.milvus_uri,
            timeout=2  # 2秒超时，快速失败
        )
    except MilvusException as e:
        logger.error(f"Milvus客户端创建失败: {e}")
        raise ConnectionError(f"Failed to connect to Milvus: {e}")

    return client


async def close_milvus_connection(client: MilvusClient):
    """
    关闭Milvus连接
    """
    try:
        client.close()
        logger.info("Milvus连接关闭成功")
    except Exception as e:
        logger.error(f"Milvus连接关闭失败: {e}")


async def verify_milvus_connection(client: MilvusClient) -> bool:
    """
    验证Milvus连接

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        # 尝试列出集合以验证连接
        version = client.get_server_version()
        logger.info(f"✓ Milvus连接成功。版本号：{version}")
        return True
    except Exception as e:
        logger.error(f"✗ Milvus连接测试失败: {e}")
        return False
