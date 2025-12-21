"""
设置线程唤醒 Temporal Schedule

使用 Temporal Schedule 定期触发线程唤醒工作流（推荐方式）

设计原则:
- 每次执行处理一个批次（AWAKENING_BATCH_SIZE 个线程）
- Temporal Schedule 自动定期触发（每 AWAKENING_SCAN_INTERVAL_HOURS 小时）
- 工作流短暂运行，无需长期占用资源
- 自然处理所有不活跃线程，无需手动分页

使用方式:
    uv run python scripts/setup_awakening_schedule.py

注意:
- 只需设置一次，Schedule 会持久化在 Temporal 中
- Schedule ID: thread-awakening-schedule
- 可通过 Temporal UI 查看和管理 Schedule
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState
)

from config import mas_config
from core.tasks.workflows import ThreadAwakeningWorkflow
from libs.factory import infra_registry
from utils import configure_logging, get_component_logger

logger = get_component_logger(__name__)


async def main():
    """设置线程唤醒 Temporal Schedule"""
    configure_logging()

    logger.info("========== 线程唤醒 Schedule 设置器 ==========")
    logger.info(f"配置:")
    logger.info(f"  - 唤醒重试间隔: {mas_config.AWAKENING_RETRY_INTERVAL_DAYS} 天")
    logger.info(f"  - 最大尝试次数: {mas_config.MAX_AWAKENING_ATTEMPTS}")
    logger.info(f"  - 批次大小: {mas_config.AWAKENING_BATCH_SIZE}")
    logger.info(f"  - 扫描间隔: {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 小时")

    try:
        # 初始化基础设施
        await infra_registry.create_clients()

        temporal_client = infra_registry.get_cached_clients().temporal
        schedule_id = "thread-awakening-schedule"

        logger.info(f"正在创建 Schedule: {schedule_id}")

        # 创建 Schedule
        schedule = Schedule(
            action=ScheduleActionStartWorkflow(
                ThreadAwakeningWorkflow.run,
                id=f"thread-awakening-{'{}'}", # {} 会被替换为时间戳
                task_queue=mas_config.TASK_QUEUE,
            ),
            spec=ScheduleSpec(
                # 每 N 小时触发一次
                intervals=[
                    ScheduleIntervalSpec(
                        every=timedelta(seconds=mas_config.scan_interval_seconds),
                    )
                ],
            ),
            state=ScheduleState(
                note="定期扫描并唤醒不活跃线程",
            ),
        )

        await temporal_client.create_schedule(
            id=schedule_id,
            schedule=schedule
        )

        logger.info("✓ Schedule 已成功创建！")
        logger.info(f"  - Schedule ID: {schedule_id}")
        logger.info(f"  - 触发间隔: 每 {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 小时")
        logger.info(f"  - 每次处理: {mas_config.AWAKENING_BATCH_SIZE} 个线程")
        logger.info(f"  - Task Queue: {mas_config.TASK_QUEUE}")
        logger.info("")
        logger.info("Schedule 将自动周期性触发工作流，无需手动干预")
        logger.info("可在 Temporal UI 中查看和管理 Schedule")

    except Exception as e:
        error_message = str(e).lower()

        if "already exists" in error_message or "schedule already exists" in error_message:
            logger.info("ℹ Schedule 已存在")
            logger.info(f"  - Schedule ID: {schedule_id}")
            logger.info("无需重复创建，Schedule 会持续运行")
            logger.info("")
            logger.info("如需修改配置:")
            logger.info("  1. 删除现有 Schedule (Temporal UI 或 CLI)")
            logger.info("  2. 重新运行此脚本")
        else:
            logger.error(f"✗ 创建 Schedule 失败: {e}", exc_info=True)
            raise

    finally:
        await infra_registry.shutdown_clients()
        logger.info("============================================")


if __name__ == "__main__":
    asyncio.run(main())
