"""
Thread Awakening Activities

线程唤醒工作流活动模块
"""

from datetime import datetime
from uuid import UUID

from temporalio import activity

from config import mas_config
from core.memory import StorageManager
from core.prompts.get_role_prompt import get_combined_system_prompt
from libs.types import Message, MessageParams
from models import Thread
from services import ThreadService
from utils import get_component_logger, get_chinese_time, get_current_datetime

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
    thread_id: UUID,
    last_interaction_at: datetime | None = None
) -> MessageParams:
    """
    准备唤醒消息上下文

    通过服务层获取线程、助手信息和对话记忆

    Args:
        tenant_id: 租户ID
        assistant_id: 助手ID
        thread_id: 线程ID
        last_interaction_at: 最后一次互动时间（可选）

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

        # 获取当前时间
        current_time = get_chinese_time()

        # 判断是否为新用户（没有对话历史或没有互动记录）
        is_new_user = not last_interaction_at or len(short_term_messages) < 3

        # 根据用户类型生成不同的指令
        if is_new_user:
            # 新用户：发送欢迎问候消息
            instructions = (
                "## 时间上下文\n"
                f"当前时间: {current_time}\n\n"
                "## 用户状态\n"
                "这是一位新用户，还没有与你进行过对话。\n\n"
                "## 任务\n"
                "生成一条热情、友好的欢迎问候消息（1-2句话，不超过50字）\n\n"
                "要求:\n"
                "1. 根据你的角色定位进行自我介绍\n"
                "2. 表达欢迎和期待与客户交流的态度\n"
                "3. 自然亲切，符合你的性格特点\n"
                "4. 可以简单提及你能提供的帮助或服务\n"
                "5. 不要过于正式或推销，保持轻松友好的语气\n\n"
                "请直接返回欢迎消息内容，不需要其他说明。"
            )
        else:
            # 老用户：发送唤醒消息
            # 计算最后一条消息距今的时间
            now = get_current_datetime()
            time_diff = now - last_interaction_at
            days = time_diff.days
            hours = int(time_diff.total_seconds() // 3600)

            if days > 0:
                time_elapsed_info = f"（上次对话是 {days} 天前）"
            elif hours > 0:
                time_elapsed_info = f"（上次对话是 {hours} 小时前）"
            else:
                minutes = int(time_diff.total_seconds() // 60)
                time_elapsed_info = f"（上次对话是 {minutes} 分钟前）"

            instructions = (
                "## 时间上下文\n"
                f"当前时间: {current_time}\n"
                f"客户已经{mas_config.INACTIVE_INTERVAL_DAYS}小时没有发消息了{time_elapsed_info}\n\n"
                "## 任务\n"
                "生成一条自然、个性化的唤醒消息（1-2句话，不超过50字）\n\n"
                "要求:\n"
                "1. 基于客户背景和对话历史，体现个性化\n"
                "2. 自然亲切，不要过于正式或推销\n"
                "3. 可以表达关怀、提供价值信息、或轻松问候\n"
                "4. 符合你的性格特点\n"
                "5. 不要使用'好久不见'这样的陈词滥调\n"
                "6. **重要**: 注意时间流逝，如果对话历史中提到的时间已经过去，请根据当前时间调整你的回复\n"
                "   例如: 如果客户说'明天见'，而现在已经是第二天了，你应该说'今天'而不是'明天'\n\n"
                "请直接返回唤醒消息内容，不需要其他说明。"
            )

        system_prompt = await get_combined_system_prompt(
            assistant_id,
            thread_id,
            instructions,
            custom_context="\n以下长期记忆可帮助回答用户问题：\n" + "\n".join(long_term)
        )

        # 构建消息序列
        prompt_sequence = [system_prompt, *short_term_messages]

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
async def update_awakened_thread(
    tenant_id: str,
    thread_id: UUID,
    content: str
) -> bool:
    """
    更新唤醒过的线程

    Args:
        tenant_id: 租户ID
        thread_id: 线程ID
        content: 助手回复内容

    Returns:
        bool: 数据库更新是否成功
    """

    logger.info(f"更新唤醒过的线程: thread_id={thread_id}")
    storage_manager = StorageManager()

    await storage_manager.store_messages(
        tenant_id=tenant_id,
        thread_id=thread_id,
        messages=[Message(role="assistant", content=content)]
    )

    # 消息发送成功，通过服务层更新数据库
    return await ThreadService.increment_awakening_attempt(thread_id)
