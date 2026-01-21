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

from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

from core.tasks.entities import TriggerMessagingResult, MessageType

with workflow.unsafe.imports_passed_through():
    from core.prompts.template_loader import get_prompt_template
    from core.tasks.activities import (
        check_thread_activity_status,
        invoke_task_llm,
        send_callback_message
    )
    from libs.types import Message, ThreadStatus


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
    async def run(self, thread_id: UUID) -> TriggerMessagingResult:
        """
        执行线程监控工作流

        Args:
            thread_id: 线程监控配置

        Returns:
            TriggerMessagingResult: 消息发送结果
        """
        # TODO: Add more detailed logging info and error exceptions
        try:
            workflow.logger.info(f"线程监控工作流开始执行: thread_id={thread_id}")

            # 1. 等待5分钟（300秒）
            await workflow.sleep(300)

            # 2. 检查线程状态是否仍为'idle'
            thread_status = await workflow.execute_activity(
                check_thread_activity_status,
                thread_id,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=self.retry_policy
            )

            # 3. 如果状态不是'idle'，说明客户已经发送了消息，不需要自动发送
            if not thread_status or thread_status != ThreadStatus.IDLE:
                workflow.logger.info(f"线程已有活动，跳过自动消息: thread_id={thread_id}, status={thread_status}")
                return TriggerMessagingResult(
                    success=True,
                    metadata={"action": "skipped", "reason": "thread_has_activity", "thread_status": str(thread_status)}
                )

            model = "google/gemini-3-flash-preview"
            provider = "openrouter"
            temperature = 0.7
            max_tokens = 1024
            context = [
                Message(role="user", content=get_prompt_template(MessageType.GREETING))
            ]
            fallback_prompt = "您好！我是您的专属助手，有什么可以帮助您的吗？"

            # 4. 线程仍为idle，生成自动消息
            content = await workflow.execute_activity(
                invoke_task_llm,
                args=[
                    model,
                    provider,
                    temperature,
                    max_tokens,
                    context,
                    fallback_prompt
                ],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=self.retry_policy
            )

            # 5. 发送消息
            result = await workflow.execute_activity(
                send_callback_message,
                args=[thread_id, content, MessageType.GREETING],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=self.retry_policy
            )

            return TriggerMessagingResult(**result)

        except Exception as e:
            return TriggerMessagingResult(
                success=False,
                detail=str(e),
                metadata={"exception_type": type(e).__name__}
            )
