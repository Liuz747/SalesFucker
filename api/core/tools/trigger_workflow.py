"""
Temporal工作流触发工具

用于异步触发Temporal工作流进行后台任务执行。
"""
import json
from uuid import UUID
from typing import Any

from infra.ops.temporal_client import get_temporal_client
from utils.logger_utils import get_component_logger

logger = get_component_logger(__name__)


async def trigger_workflow(
    tenant_id: str,
    workflow_name: str,
    payload: dict[str, Any]
) -> dict:
    """
    触发异步Temporal工作流

    启动指定的Temporal工作流进行后台任务执行和事件调度。

    Args:
        tenant_id: 租户标识符
        workflow_name: Temporal工作流名称
        payload: 传递给工作流的JSON载荷

    Returns:
        dict: 包含工作流执行结果的响应字典
            - success: bool, 是否成功
            - workflow_id: str, 工作流实例ID
            - workflow_name: str, 工作流名称
            - status: str, 工作流状态
    """
    try:
        logger.info(f"开始触发工作流 - 租户: {tenant_id}, 工作流: {workflow_name}")

        # 获取Temporal客户端
        temporal_client = await get_temporal_client()

        # 构建工作流ID（包含租户隔离）	
        workflow_id = f"{tenant_id}-{workflow_name}-{UUID().hex[:8]}"

        # 动态导入工作流类（基于工作流名称）
        workflow_class = await _get_workflow_class(workflow_name)
        if not workflow_class:
            logger.error(f"未找到工作流类: {workflow_name}")
            return {
                "success": False,
                "workflow_id": None,
                "workflow_name": workflow_name,
                "status": "failed",
                "error": f"工作流类不存在: {workflow_name}"
            }

        # 启动工作流
        workflow_handle = await temporal_client.start_workflow(
            workflow_class.run,
            payload,
            id=workflow_id,
            task_queue=f"mas-{tenant_id}",  # 租户专用任务队列
        )

        response = {
            "success": True,
            "workflow_id": workflow_handle.id,
            "workflow_name": workflow_name,
            "status": "started",
            "task_queue": f"mas-{tenant_id}",
            "payload_size": len(json.dumps(payload)) if payload else 0
        }

        logger.info(f"工作流启动成功 - ID: {workflow_handle.id}")
        return response

    except Exception as e:
        logger.error(f"工作流触发失败: {e}")
        return {
            "success": False,
            "workflow_id": None,
            "workflow_name": workflow_name,
            "status": "failed",
            "error": str(e)
        }


async def _get_workflow_class(workflow_name: str):
    """
    根据工作流名称动态获取工作流类

    Args:
        workflow_name: 工作流名称

    Returns:
        工作流类或None
    """
    try:
        # 映射工作流名称到模块路径
        workflow_mapping = {
            "greeting_workflow": "core.tasks.workflows.greeting_workflow.GreetingWorkflow",
            "ice_breaking_workflow": "core.tasks.workflows.ice_breaking_workflow.IceBreakingWorkflow",
            "follow_up_workflow": "core.tasks.workflows.follow_up_workflow.FollowUpWorkflow",
            "holiday_broadcast_workflow": "core.tasks.workflows.holiday_broadcast_workflow.HolidayBroadcastWorkflow",
            "marketing_campaign_workflow": "core.tasks.workflows.marketing_campaign_workflow.MarketingCampaignWorkflow",
            "scheduled_messaging_workflow": "core.tasks.workflows.scheduled_messaging_workflow.ScheduledMessagingWorkflow",
        }

        if workflow_name not in workflow_mapping:
            logger.warning(f"未知工作流名称: {workflow_name}")
            return None

        # 动态导入模块和类
        module_path, class_name = workflow_mapping[workflow_name].rsplit(".", 1)

        # 使用 importlib 动态导入
        import importlib
        module = importlib.import_module(module_path)
        workflow_class = getattr(module, class_name)

        return workflow_class

    except Exception as e:
        logger.error(f"工作流类导入失败 - {workflow_name}: {e}")
        return None