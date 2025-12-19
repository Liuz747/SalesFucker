"""Conversation Preservation Activities"""
from datetime import timedelta
from uuid import UUID

from temporalio import activity

from config import mas_config
from core.memory import (
    ConversationStore,
    ElasticsearchIndex,
    StorageManager,
    SummarizationService,
    conversation_quality_evaluator
)
from libs.types import MemoryType
from utils import get_component_logger, get_current_datetime, get_current_timestamp

logger = get_component_logger(__name__)


@activity.defn
async def check_preservation_needed(thread_id: UUID) -> dict:
    """
    检查对话是否需要保存

    Args:
        thread_id: 对话线程ID

    Returns:
        dict包含:
        - needs_preservation: 是否需要保存
        - reason: 原因说明
        - message_count: 消息数量
        - exists: 对话是否存在
    """
    try:
        conversation_store = ConversationStore()

        # 获取消息数量
        message_count = await conversation_store.get_message_count(thread_id)

        # 对话不存在
        if message_count == 0:
            logger.info(f"对话不存在于Redis: thread_id={thread_id}")
            return {
                "needs_preservation": False,
                "reason": "conversation_not_found_in_redis",
                "message_count": 0,
                "exists": False
            }

        # 快速检查：如果消息数>=15会自动摘要，无需保存
        if message_count >= 15:
            logger.info(f"对话将自动摘要，无需保存: thread_id={thread_id}, count={message_count}")
            return {
                "needs_preservation": False,
                "reason": "will_auto_summarize",
                "message_count": message_count,
                "exists": True
            }

        # 检查最小消息数
        if message_count < mas_config.MIN_MESSAGES_TO_PRESERVE:
            logger.info(
                f"消息数不足，跳过保存: thread_id={thread_id}, "
                f"count={message_count} < {mas_config.MIN_MESSAGES_TO_PRESERVE}"
            )
            return {
                "needs_preservation": False,
                "reason": "too_few_messages",
                "message_count": message_count,
                "exists": True
            }

        logger.info(f"对话需要保存检查: thread_id={thread_id}, message_count={message_count}")

        return {
            "needs_preservation": True,
            "reason": "meets_criteria",
            "message_count": message_count,
            "exists": True
        }

    except Exception as e:
        logger.error(f"检查保存需求失败: thread_id={thread_id}, error={e}", exc_info=True)
        raise


@activity.defn
async def evaluate_conversation_quality(thread_id: UUID) -> dict:
    """
    评估对话质量

    Args:
        thread_id: 对话线程ID

    Returns:
        dict包含:
        - should_preserve: 是否应该保存
        - evaluation: 评估详情
        - message_count: 消息数量
    """
    try:
        conversation_store = ConversationStore()

        # 获取消息数量和消息内容
        messages = await conversation_store.get_recent(thread_id)
        message_count = len(messages)

        if not messages:
            logger.warning(f"未找到消息用于质量评估: thread_id={thread_id}")
            return {
                "should_preserve": False,
                "evaluation": {
                    "passed_checks": [],
                    "failed_checks": ["no_messages_found"]
                },
                "message_count": 0
            }

        # 执行质量评估
        should_preserve, evaluation = conversation_quality_evaluator(messages)

        logger.info(
            f"对话质量评估完成: thread_id={thread_id}, "
            f"should_preserve={should_preserve}, "
            f"passed={len(evaluation['passed_checks'])}, "
            f"failed={len(evaluation['failed_checks'])}"
        )

        return {
            "should_preserve": should_preserve,
            "evaluation": evaluation,
            "message_count": message_count
        }

    except Exception as e:
        logger.error(f"质量评估失败: thread_id={thread_id}, error={e}", exc_info=True)
        raise


@activity.defn
async def preserve_conversation_to_elasticsearch(
    thread_id: UUID,
    tenant_id: str
) -> dict:
    """
    保存对话到Elasticsearch

    Args:
        thread_id: 对话线程ID
        tenant_id: 租户ID

    Returns:
        dict:
        - success: 是否成功
        - doc_id: Elasticsearch文档ID（成功时）
        - summary_length: 摘要长度（成功时）
        - message_count: 消息数量
    """
    try:
        conversation_store = ConversationStore()
        elasticsearch_index = ElasticsearchIndex()
        summarization_service = SummarizationService()

        # 获取消息
        messages = await conversation_store.get_recent(thread_id)

        if not messages:
            logger.error(f"保存失败：未找到消息: thread_id={thread_id}")
            return {"success": False, "error": "no_messages_found"}

        # 生成摘要
        text_block = "\n".join([
            f"{msg.role}: {StorageManager.extract_text(msg.content)}"
            for msg in messages
        ])

        logger.info(f"生成对话摘要: thread_id={thread_id}, messages={len(messages)}")
        summary_content = await summarization_service.generate_summary(text_block)

        if not summary_content:
            logger.error(f"摘要生成失败: thread_id={thread_id}")
            return {"success": False, "error": "summary_generation_failed"}

        # 存储到Elasticsearch
        doc_id = await elasticsearch_index.store_summary(
            tenant_id=tenant_id,
            thread_id=thread_id,
            content=summary_content,
            memory_type=MemoryType.LONG_TERM,
            expires_at=get_current_datetime() + timedelta(days=mas_config.ES_MEMORY_TTL_DAYS),
            tags=[
                "auto_preserved_short",
                "conversation_summary"
            ],
            importance_score=0.7,
            metadata={
                "preservation_type": "auto_short_conversation",
                "message_count": len(messages),
                "preserved_at": get_current_timestamp()
            }
        )

        await conversation_store.shrink_context(thread_id)

        logger.info(
            f"对话保存成功: thread_id={thread_id}, "
            f"doc_id={doc_id}, "
            f"summary_length={len(summary_content)}, "
            f"message_count={len(messages)}"
        )

        return {
            "success": True,
            "doc_id": doc_id,
            "summary_length": len(summary_content),
            "message_count": len(messages)
        }

    except Exception as e:
        logger.error(
            f"保存到Elasticsearch失败: thread_id={thread_id}, error={e}",
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "exception_type": type(e).__name__
        }
