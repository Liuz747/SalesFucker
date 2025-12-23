from uuid import UUID

from temporalio import activity

from config import mas_config
from utils import get_component_logger, ExternalClient

logger = get_component_logger(__name__)


@activity.defn
async def send_callback_message(
    thread_id: UUID,
    content: str,
    task_name: str,
    endpoint: str
) -> dict:
    """
    通过API发送自动消息

    Args:
        thread_id: 线程ID
        content: 消息内容
        task_name: 任务名称
        endpoint: API接口路径

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
            endpoint=endpoint,
            data=payload,
            headers={"User-Agent": "MAS-Background-Processor/1.0"},
            timeout=30.0,
            max_retries=3
        )

        logger.info(f"自动消息发送成功: thread_id={thread_id}")
        return {"success": True}

    except Exception as e:
        logger.error(f"发送自动消息失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }