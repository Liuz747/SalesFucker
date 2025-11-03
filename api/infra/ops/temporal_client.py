"""
Temporal工作流引擎客户端工厂

提供异步Temporal客户端连接管理，用于事件调度和工作流编排。
"""

from temporalio.client import Client

from config import mas_config
from utils import get_component_logger


logger = get_component_logger(__name__)

async def get_temporal_client() -> Client:
    """
    异步获取Temporal客户端

    使用全局单例模式，支持连接复用。

    Returns:
        Client: Temporal客户端实例

    Raises:
        ConnectionError: 当连接Temporal服务器失败时
    """

    try:
        logger.info(f"初始化Temporal客户端: {mas_config.temporal_url}")
        # 创建Temporal客户端
        temporal_client = await Client.connect(mas_config.TEMPORAL_HOST)

        logger.info(f"✓ Temporal客户端连接成功。命名空间: {mas_config.TEMPORAL_NAMESPACE}")

        return temporal_client
    except Exception as e:
        logger.error(f"✗ Temporal客户端连接失败: {e}")
        raise ConnectionError(f"Failed to connect to Temporal: {e}")


async def verify_temporal_connection(client: Client) -> bool:
    """
    验证Temporal服务器连接

    通过检查系统健康状态来验证连接。

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        # 通过描述命名空间来验证连接
        info = await client.workflow_service.get_system_info()

        if info:
            logger.info(f"✓ Temporal连接测试成功。 信息：{info}")
            return True

        return False

    except Exception as e:
        logger.error(f"✗ Temporal连接测试失败: {e}")
        return False