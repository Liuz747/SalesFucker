"""
Temporal消息工作器入口

启动Temporal工作器处理消息调度任务。

使用方式:
    uv run temporal-worker.py
"""

import asyncio
from temporalio.worker import Worker

from config import mas_config
from libs.factory import infra_registry
from core.tasks.workflows import get_all_workflows
from core.tasks.activities import get_all_activities
from utils import configure_logging, get_component_logger

logger = get_component_logger(__name__)


async def main():
    """启动Temporal工作器"""
    configure_logging()

    # 初始化基础设施
    await infra_registry.create_clients()
    await infra_registry.test_clients()

    # 创建工作器
    worker = Worker(
        infra_registry._clients.temporal,
        task_queue=mas_config.TASK_QUEUE,
        workflows=get_all_workflows(),
        activities=get_all_activities(),
        max_concurrent_activities=mas_config.MAX_CONCURRENT_ACTIVITIES,
        max_concurrent_workflow_tasks=mas_config.WORKER_COUNT
    )

    logger.info(f"Temporal工作器已启动，任务队列: {mas_config.TASK_QUEUE}")

    try:
        await worker.run()
    finally:
        await infra_registry.shutdown_clients()


if __name__ == "__main__":
    asyncio.run(main())