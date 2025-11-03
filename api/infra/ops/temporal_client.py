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

    创建与Temporal服务器的连接实例，用于工作流执行和任务调度。

    Returns:
        Client: Temporal客户端实例

    Raises:
        ConnectionError: 当连接Temporal服务器失败时
    """

    try:
        # 创建Temporal客户端
        temporal_client = await Client.connect(mas_config.temporal_url)
        return temporal_client
    except Exception as e:
        logger.error(f"✗ Temporal客户端连接失败: {e}")
        raise ConnectionError(f"Failed to connect to Temporal: {e}")


async def verify_temporal_connection(client: Client) -> bool:
    """
    验证Temporal服务器连接

    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        return await client.service_client.check_health()

    except Exception as e:
        logger.error(f"✗ Temporal连接测试失败: {e}")
        return False