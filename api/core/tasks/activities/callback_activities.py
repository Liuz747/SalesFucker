"""
简单线程监控活动

提供简单的线程监控所需的活动函数，只做必要的操作:
1. 检查线程状态
2. 生成自动消息
3. 发送消息
"""

from temporalio import activity

from config import mas_config
from utils import get_component_logger, ExternalClient
from core.tasks.entities import MessagingResult

logger = get_component_logger(__name__)


@activity.defn
async def send_callback_message(thread_id: str, content: str, task_name: str) -> MessagingResult:
    """
    通过API发送自动消息

    Args:
        thread_id: 线程ID
        content: 消息内容
        task_name: 任务名称

    Returns:
        MessagingResult: 发送结果
    """
    try:
        logger.info(f"发送自动消息: thread_id={thread_id}")

        callback_url = str(mas_config.CALLBACK_URL)

        client = ExternalClient(base_url=callback_url)

        payload = {
            "thread_id": thread_id,
            "content": content,
            "sender_type": "assistant",
            "message_type": task_name,
        }

        response = await client.make_request(
            method="POST",
            endpoint="/api",
            data=payload,
            headers={"User-Agent": "MAS-Background-Processor/1.0"},
            timeout=30.0,
            max_retries=3
        )

        result = MessagingResult(
            success=True,
            metadata={
                "thread_id": thread_id,
                "trigger": task_name,
                "content_length": len(content)
            }
        )

        logger.info(f"自动消息发送成功: thread_id={thread_id}")
        return result

    except Exception as e:
        logger.error(f"发送自动消息失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
        return MessagingResult(
            success=False,
            error_message=str(e),
            metadata={"exception_type": type(e).__name__, "thread_id": thread_id}
        )