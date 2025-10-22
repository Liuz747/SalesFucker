"""
Milvus客户端工厂

提供Milvus向量数据库连接管理。
"""

from pymilvus import connections, MilvusException

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)

_connected: bool = False


async def get_milvus_connection():
    """
    获取Milvus连接

    使用全局连接状态管理。
    """
    global _connected

    if not _connected:
        try:
            logger.info(f"初始化Milvus连接: {mas_config.MILVUS_HOST}:{mas_config.MILVUS_PORT}")
            connections.connect(
                alias="default",
                host=mas_config.MILVUS_HOST,
                port=mas_config.MILVUS_PORT,
                timeout=2  # 2秒超时，快速失败
            )
            _connected = True
            logger.info("Milvus连接成功")
        except MilvusException as e:
            logger.error(f"Milvus连接失败: {e}")
            raise ConnectionError(f"Failed to connect to Milvus: {e}")


async def close_milvus_connection():
    """
    关闭Milvus连接
    """
    global _connected

    if _connected:
        try:
            connections.disconnect("default")
            _connected = False
            logger.info("Milvus连接关闭成功")
        except Exception as e:
            logger.error(f"Milvus连接关闭失败: {e}")


async def verify_milvus_connection() -> bool:
    """
    验证Milvus连接

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        await get_milvus_connection()
        logger.info("Milvus连接测试成功")
        return True
    except Exception as e:
        logger.error(f"Milvus连接测试失败: {e}")
        return False
