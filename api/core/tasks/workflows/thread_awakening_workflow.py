"""
Thread Awakening Workflow

周期性线程唤醒工作流，扫描所有不活跃线程并发送个性化唤醒消息
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# 安全导入活动和配置
with workflow.unsafe.imports_passed_through():
    from core.tasks.activities import (
        invoke_task_llm,
        scan_inactive_threads,
        send_callback_message,
        prepare_awakening_context,
        update_awakened_thread
    )
    from libs.types import MessageType


@workflow.defn
class ThreadAwakeningWorkflow:
    """
    线程唤醒工作流 - 单批次处理不活跃线程

    设计原则:
    - 每次执行处理一个批次（AWAKENING_BATCH_SIZE 个线程）
    - 由 Temporal Schedule 定期触发（每 AWAKENING_SCAN_INTERVAL_HOURS 小时）
    - 无需手动分页，自然处理所有不活跃线程
    """

    def __init__(self):
        self.retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            non_retryable_error_types=["ValidationError"]
        )

    @workflow.run
    async def run(self) -> dict:
        """
        执行单批次线程唤醒工作流

        流程:
        1. 扫描一个批次的不活跃线程
        2. 对每个线程：准备上下文 → 生成消息 → 发送消息
        3. 返回处理统计

        Returns:
            dict: 处理统计信息
        """
        workflow.logger.info("========== 线程唤醒工作流开始 ==========")

        # 初始化统计数据
        stats = {
            "processed": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0
        }

        # Step 1: 扫描不活跃线程
        workflow.logger.info(f"扫描不活跃线程")

        threads = await workflow.execute_activity(
            scan_inactive_threads,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

        workflow.logger.info(f"找到 {len(threads)} 个不活跃线程")

        if not threads:
            workflow.logger.info("没有不活跃线程需要处理")
            return {
                "status": "completed",
                "stats": stats
            }

        model = "anthropic/claude-haiku-4.5"
        provider = "openrouter"
        temperature = 0.8
        max_tokens = 1024
        fallback_prompt = "最近怎么样？"

        # Step 2: 处理每个线程
        for thread_data in threads:
            try:
                thread_id = thread_data.thread_id
                workflow.logger.info(
                    f"处理线程: {getattr(thread_data, 'name', None)} (id={thread_id}, "
                    f"attempt={thread_data.awakening_attempt_count})"
                )

                # 检查线程是否有助手
                if not thread_data.assistant_id:
                    workflow.logger.warning(f"线程无助手，跳过: thread_id={thread_id}")
                    stats["skipped"] += 1
                    continue

                # Step 3: 准备唤醒上下文（会验证助手状态）
                workflow.logger.info(f"准备唤醒上下文: thread_id={thread_id}")
                context = await workflow.execute_activity(
                    prepare_awakening_context,
                    args=[thread_data.tenant_id, thread_data.assistant_id, thread_id],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=self.retry_policy
                )

                # Step 4: 生成唤醒消息
                workflow.logger.info(f"生成唤醒消息: thread_id={thread_id}")
                response = await workflow.execute_activity(
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

                workflow.logger.info(f"消息生成完成: thread_id={thread_id}")

                # Step 5: 发送唤醒消息
                workflow.logger.info(f"发送唤醒消息: thread_id={thread_id}")
                send_result = await workflow.execute_activity(
                    send_callback_message,
                    args=[
                        thread_data.assistant_id,
                        thread_id,
                        response.content,
                        MessageType.AWAKENING,
                        "/chat/ai/hook/event"
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=self.retry_policy
                )

                # Step 6: 更新线程唤醒计数
                if send_result.get("success"):
                    workflow.logger.info(f"更新线程唤醒计数: thread_id={thread_id}")
                    update_result = await workflow.execute_activity(
                        update_awakened_thread,
                        args=[thread_id],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=self.retry_policy
                    )

                    if update_result.get("success"):
                        stats["sent"] += 1
                        workflow.logger.info(
                            f"✓ 唤醒消息发送成功并已更新计数: thread_id={thread_id}"
                        )
                    else:
                        stats["failed"] += 1
                        workflow.logger.error(
                            f"✗ 消息发送成功但更新计数失败: thread_id={thread_id}, "
                            f"error={update_result.get('error', 'unknown')}"
                        )
                else:
                    stats["failed"] += 1
                    workflow.logger.error(
                        f"✗ 唤醒消息发送失败: thread_id={thread_id}, "
                        f"error={send_result.get('error', 'unknown')}"
                    )

                stats["processed"] += 1

            except Exception as e:
                # 线程级别异常：记录错误，继续处理下一个线程
                stats["failed"] += 1
                workflow.logger.error(
                    f"✗ 处理线程异常: thread_id={thread_data.thread_id}, "
                    f"error={type(e).__name__}: {str(e)}"
                )
                continue

        # 工作流完成统计
        workflow.logger.info("========== 线程唤醒工作流完成 ==========")
        workflow.logger.info(
            f"统计: 处理={stats['processed']}, 成功={stats['sent']}, "
            f"跳过={stats['skipped']}, 失败={stats['failed']}"
        )

        return {
            "status": "completed",
            "stats": stats
        }
