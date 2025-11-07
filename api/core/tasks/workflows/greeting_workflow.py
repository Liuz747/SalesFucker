"""
开场白工作流

当线程创建后，等待5分钟，如果线程状态仍为'idle'（无客户输入），
则自动生成并发送一条消息。

流程:
1. 线程创建 (status = 'idle')
2. 等待5分钟
3. 检查线程状态
4. 如果仍为'idle' -> 调用LLM -> 发送消息
5. 如果为'active' -> 什么都不做
"""

import asyncio
from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

from core.tasks.workflow_entities import MessagingResult

# Note: Activities should not be imported directly in workflows.
# Instead, we reference them by name in workflow.execute_activity().


@workflow.defn
class GreetingWorkflow:
    """简单线程监控工作流"""

    def __init__(self):
        self.retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            non_retryable_error_types=["ValidationError", "PermissionError"]
        )

    @workflow.run
    async def run(self, thread_id: UUID) -> MessagingResult:
        """
        执行线程监控工作流

        Args:
            thread_id: 线程监控配置

        Returns:
            MessagingResult: 消息发送结果
        """
        try:
            # Note: logger is not available in workflow sandbox, remove logging

            # 1. 等待5分钟（300秒）
            await asyncio.sleep(10)

            # 2. 检查线程状态是否仍为'idle'
            thread_status = await workflow.execute_activity(
                "check_thread_activity_status",
                thread_id,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self.retry_policy
            )

            # 3. 如果状态不是'idle'，说明客户已经发送了消息，不需要自动发送
            if thread_status != 'IDLE':
                return MessagingResult(
                    success=True,
                    metadata={"action": "skipped", "reason": "thread_has_activity", "thread_status": thread_status}
                )

            # 4. 线程仍为idle，生成自动消息
            content = await workflow.execute_activity(
                "invoke_task_llm",
                thread_id,
                "greeting",
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=self.retry_policy
            )

            # 5. 发送消息
            result = await workflow.execute_activity(
                "send_callback_message",
                thread_id,
                content,
                "greeting",
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=self.retry_policy
            )

            return result

        except Exception as e:
            return MessagingResult(
                success=False,
                error_message=str(e),
                metadata={"exception_type": type(e).__name__}
            )
