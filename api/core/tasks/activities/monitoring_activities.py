"""
线程监控活动

提供线程活动监控所需的Temporal活动函数。
这些活动用于检查线程的消息活动状态，生成自动消息，并发送监控消息。

主要功能:
- 检查线程活动状态
- 获取最后消息时间
- 生成监控提醒消息
- 发送自动监控消息
"""

from uuid import UUID

from temporalio import activity

from models import ThreadStatus
from services import ThreadService
from utils import get_component_logger

logger = get_component_logger(__name__)


@activity.defn
async def check_thread_activity_status(thread_id: UUID) -> ThreadStatus:
    """检查线程活动状态"""
    try:
        # 使用消息服务获取线程的最新活动状态
        logger.info(f"检查线程活动状态: thread_id={thread_id}")
        thread = await ThreadService.get_thread(thread_id)

        if thread:
            return thread.status

    except Exception as e:
        logger.error(f"检查线程活动状态失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
        raise

