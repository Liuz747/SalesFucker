"""
Conversation Preservation Workflow

自动保存短期对话到长期存储的Temporal工作流
"""
from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

from core.tasks.entities import TriggerMessagingResult

# 在Temporal工作流中安全导入activities
with workflow.unsafe.imports_passed_through():
    from core.tasks.activities.preservation_activities import (
        check_preservation_needed,
        evaluate_conversation_quality,
        preserve_conversation_to_elasticsearch
    )
    from config import mas_config


@workflow.defn
class ConversationPreservationWorkflow:
    """对话保存工作流"""

    def __init__(self):
        self.retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            non_retryable_error_types=["ValidationError", "ThreadNotFoundException"]
        )

    @workflow.run
    async def run(self, thread_id: UUID, tenant_id: str) -> TriggerMessagingResult:
        """
        执行对话保存工作流

        Args:
            thread_id: 对话线程ID
            tenant_id: 租户ID

        Returns:
            PreservationResult: 保存结果
        """
        workflow.logger.info(f"对话保存工作流启动: thread_id={thread_id}, tenant_id={tenant_id}")

        try:
            # Step 1: 等待到触发时间点（TTL - 45分钟）
            wait_seconds = mas_config.preservation_wait_seconds

            workflow.logger.info(
                f"等待 {wait_seconds}秒 ({wait_seconds/3600:.1f}小时) 后检查对话: thread_id={thread_id}"
            )
            await workflow.sleep(wait_seconds)

            # Step 2: 检查是否需要保存
            workflow.logger.info(f"检查对话是否需要保存: thread_id={thread_id}")
            check_result = await workflow.execute_activity(
                check_preservation_needed,
                args=[thread_id],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self.retry_policy
            )

            if not check_result["needs_preservation"]:
                reason = check_result.get("reason", "unknown")
                workflow.logger.info(f"对话无需保存: thread_id={thread_id}, reason={reason}")
                return TriggerMessagingResult(
                    success=True,
                    action="skipped",
                    detail=reason,
                    metadata=check_result
                )

            # Step 3: 评估对话质量
            workflow.logger.info(f"评估对话质量: thread_id={thread_id}")
            quality_result = await workflow.execute_activity(
                evaluate_conversation_quality,
                args=[thread_id],
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=self.retry_policy
            )

            if not quality_result["should_preserve"]:
                workflow.logger.info(
                    f"对话质量不足，跳过保存: thread_id={thread_id}"
                )
                return TriggerMessagingResult(
                    success=True,
                    action="filtered",
                    detail="quality_check_failed",
                    metadata=quality_result
                )

            # Step 4: 保存到Elasticsearch
            workflow.logger.info(f"保存对话到Elasticsearch: thread_id={thread_id}")
            preserve_result = await workflow.execute_activity(
                preserve_conversation_to_elasticsearch,
                args=[thread_id, tenant_id],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=self.retry_policy
            )

            if preserve_result["success"]:
                workflow.logger.info(
                    f"对话保存成功: thread_id={thread_id}, "
                    f"doc_id={preserve_result.get('doc_id')}, "
                    f"message_count={preserve_result.get('message_count')}"
                )
                return TriggerMessagingResult(
                    success=True,
                    action="preserved",
                    detail="quality_passed",
                    metadata=preserve_result
                )
            else:
                workflow.logger.error(
                    f"对话保存失败: thread_id={thread_id}, "
                    f"error={preserve_result.get('error')}"
                )
                return TriggerMessagingResult(
                    success=False,
                    action="preservation_failed",
                    detail=preserve_result.get("error", "unknown_error"),
                    metadata=preserve_result
                )

        except Exception as e:
            workflow.logger.error(
                f"工作流执行异常: thread_id={thread_id}, error={str(e)}",
                exc_info=True
            )
            return TriggerMessagingResult(
                success=False,
                action="workflow_error",
                detail=str(e),
                metadata={"exception_type": type(e).__name__}
            )
