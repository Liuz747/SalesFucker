import json
from uuid import UUID

from temporalio import activity

from config import mas_config
from utils import get_component_logger, ExternalClient, get_current_timestamp_ms

logger = get_component_logger(__name__)


@activity.defn
async def send_callback_message(
    assistant_id: UUID,
    thread_id: UUID,
    content: str,
    task_name: str,
    endpoint: str
) -> dict:
    """
    通过API发送自动消息

    Args:
        assistant_id: 助手ID
        thread_id: 线程ID
        content: 消息内容
        task_name: 任务名称
        endpoint: API接口路径

    Returns:
        dict: 发送结果
    """
    try:
        logger.info(f"发送自动消息: thread_id={thread_id}")

        callback_url = str(mas_config.CALLBACK_URL)
        client = ExternalClient(base_url=callback_url)

        event_content = {
            "active_chat_response": content
        }

        payload = {
            "assistantId": str(assistant_id),
            "threadId": str(thread_id),
            "eventId": task_name,
            "eventTime": get_current_timestamp_ms(),
            "eventContent": json.dumps(event_content, ensure_ascii=False),
        }

        response = await client.make_request(
            method="POST",
            endpoint=endpoint,
            data=payload,
            headers={"User-Agent": "MAS-Background-Processor/1.0"},
            timeout=30.0,
            max_retries=3
        )

        if response.get("code") == 200:
            logger.info(f"自动消息发送成功: thread_id={thread_id}")
            return {"success": True}
        else:
            logger.error(f"自动消息发送失败: thread_id={thread_id}, 错误: {response.get('msg')}")
            return {
                "success": False,
                "error": response.get("msg")
            }

    except Exception as e:
        logger.error(f"发送自动消息失败: thread_id={thread_id}, 错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }