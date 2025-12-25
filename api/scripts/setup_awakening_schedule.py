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
- 如果 Schedule 已存在，会自动更新配置（支持配置热更新）
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
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleAlreadyRunningError
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
    # 临时测试修改
    # logger.info(f"  - 唤醒重试间隔: {mas_config.AWAKENING_RETRY_INTERVAL_DAYS} 天")
    logger.info(f"  - 唤醒重试间隔: {mas_config.AWAKENING_RETRY_INTERVAL_DAYS} 分钟")
    logger.info(f"  - 最大尝试次数: {mas_config.MAX_AWAKENING_ATTEMPTS}")
    logger.info(f"  - 批次大小: {mas_config.AWAKENING_BATCH_SIZE}")
    # 临时测试修改
    # logger.info(f"  - 扫描间隔: {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 小时")
    logger.info(f"  - 扫描间隔: {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 分钟")

    try:
        # 初始化基础设施
        await infra_registry.create_clients()

        temporal_client = infra_registry.get_cached_clients().temporal
        schedule_id = "thread-awakening-schedule"

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
                        # 临时测试修改
                        # every=timedelta(hours=mas_config.AWAKENING_SCAN_INTERVAL_HOURS),
                        every=timedelta(minutes=mas_config.AWAKENING_SCAN_INTERVAL_HOURS),
                    )
                ],
            ),
            state=ScheduleState(
                note="定期扫描并唤醒不活跃线程",
            ),
        )

        # 尝试创建 Schedule
        try:
            logger.info(f"正在创建 Schedule: {schedule_id}")
            await temporal_client.create_schedule(
                id=schedule_id,
                schedule=schedule
            )
            logger.info("✓ Schedule 已成功创建！")
            logger.info(f"  - Schedule ID: {schedule_id}")
            # 临时测试修改
            # logger.info(f"  - 触发间隔: 每 {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 小时")
            logger.info(f"  - 触发间隔: 每 {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 分钟")
            logger.info(f"  - 每次处理: {mas_config.AWAKENING_BATCH_SIZE} 个线程")
            logger.info(f"  - Task Queue: {mas_config.TASK_QUEUE}")

        except ScheduleAlreadyRunningError:
            # 处理 Schedule 已存在/运行中的情况
            logger.info(f"ℹ Schedule 已存在，正在更新配置...")

            # 获取现有 Schedule handle并更新
            schedule_handle = temporal_client.get_schedule_handle(schedule_id)
            await schedule_handle.update(
                lambda input: ScheduleUpdate(
                    schedule=Schedule(
                        action=schedule.action,
                        spec=schedule.spec,
                        state=schedule.state,
                    )
                )
            )

            logger.info("✓ Schedule 已成功更新！")
            logger.info(f"  - Schedule ID: {schedule_id}")
            # 临时测试修改
            # logger.info(f"  - 触发间隔: 每 {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 小时")
            logger.info(f"  - 触发间隔: 每 {mas_config.AWAKENING_SCAN_INTERVAL_HOURS} 分钟")
            logger.info(f"  - 每次处理: {mas_config.AWAKENING_BATCH_SIZE} 个线程")
            logger.info(f"  - Task Queue: {mas_config.TASK_QUEUE}")

        logger.info("")
        logger.info("Schedule 将自动周期性触发工作流，无需手动干预")
        logger.info("可在 Temporal UI 中查看和管理 Schedule")

    except Exception as e:
        logger.error(f"✗ Schedule 设置失败: {e}", exc_info=True)
        raise

    finally:
        await infra_registry.shutdown_clients()
        logger.info("============================================")


if __name__ == "__main__":
    asyncio.run(main())
