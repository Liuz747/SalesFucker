"""
Thread Awakening Activities

线程唤醒工作流活动模块
遵循最佳实践：通过服务层调用，避免直接数据库访问
"""

from uuid import UUID

from temporalio import activity

from config import mas_config
from core.memory import StorageManager
from core.prompts.get_role_prompt import get_combined_system_prompt
from libs.types import Message, MessageParams
from models import Thread
from services import ThreadService
from utils import get_component_logger

logger = get_component_logger(__name__)


@activity.defn
async def scan_inactive_threads() -> list[Thread]:
    """
    扫描不活跃线程

    通过 ThreadService 查询不活跃线程。

    Returns:
        list: 线程列表
    """
    try:
        logger.info("扫描不活跃线程")

        # 通过服务层获取不活跃线程
        return await ThreadService.get_inactive_threads_for_awakening()

    except Exception as e:
        logger.error(f"扫描不活跃线程失败: error={e}", exc_info=True)
        raise


@activity.defn
async def prepare_awakening_context(
    tenant_id: str,
    assistant_id: UUID,
    thread_id: UUID
) -> MessageParams:
    """
    准备唤醒消息上下文

    通过服务层获取线程、助手信息和对话记忆

    Args:
        tenant_id: 租户ID
        assistant_id: 助手ID
        thread_id: 线程ID

    Returns:
        list: 包含短期消息、长期记忆、客户资料和助手资料的上下文
    """
    try:
        logger.info(f"准备唤醒上下文: thread_id={thread_id}")

        # 通过StorageManager获取对话历史和长期记忆
        storage_manager = StorageManager()
        short_term_messages, long_term_list = await storage_manager.retrieve_context(
            tenant_id=tenant_id,
            thread_id=thread_id,
            es_limit=5
        )

        long_term = []
        for idx, summary in enumerate(long_term_list, 1):
            content = summary.get("content") or ""
            tags = summary.get("tags") or []
            tag_display = (
                f" (标签: {', '.join(str(tag) for tag in tags)})"
                if tags
                else ""
            )
            long_term.append(f"{idx}. {content}{tag_display}")

        instructions = (
            "## 任务\n"
            # 临时测试修改
            # f"客户已经{mas_config.AWAKENING_RETRY_INTERVAL_DAYS}天没有发消息了\n"
            f"客户已经{mas_config.AWAKENING_RETRY_INTERVAL_DAYS}分钟没有发消息了\n"
            "生成一条自然、个性化的唤醒消息（1-2句话，不超过50字）\n\n"
            "要求:\n"
            "1. 基于客户背景和对话历史，体现个性化\n"
            "2. 自然亲切，不要过于正式或推销\n"
            "3. 可以表达关怀、提供价值信息、或轻松问候\n"
            "4. 符合你的性格特点\n"
            "5. 不要使用'好久不见'这样的陈词滥调\n"
            "请直接返回唤醒消息内容，不需要其他说明。"
        )

        system_prompt = await get_combined_system_prompt(
            assistant_id,
            thread_id,
            instructions,
            custom_context="\n以下长期记忆可帮助回答用户问题：\n" + "\n".join(long_term)
        )

        # 构建消息序列
        prompt_sequence = [system_prompt] + short_term_messages

        # 确保最后一条消息是用户消息
        if prompt_sequence[-1].role != "user":
            prompt_sequence.append(
                Message(role="user", content="请根据以上对话历史，生成一条唤醒消息。")
            )

        logger.info(f"上下文准备完成: thread_id={thread_id}")

        return prompt_sequence

    except Exception as e:
        logger.error(f"准备唤醒上下文失败: thread_id={thread_id}, error={e}", exc_info=True)
        raise


@activity.defn
async def update_awakened_thread(thread_id: UUID) -> dict:
    """
    更新唤醒过的线程

    Returns:
        list: 线程列表
    """
    # 消息发送成功，通过服务层更新数据库
    success = await ThreadService.increment_awakening_attempt(thread_id)

    if not success:
        logger.error(f"更新线程唤醒计数失败: thread_id={thread_id}")
        return {"success": False, "error": "database_update_failed"}

    logger.info(f"线程更新成功: thread_id={thread_id}")

    return {"success": True}