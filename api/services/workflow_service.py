"""
工作流执行业务服务层

"""

from uuid import UUID

from fastapi import HTTPException

from models import Thread
from services.thread_service import ThreadService
from services.assistant_service import AssistantService
from utils import get_component_logger

logger = get_component_logger(__name__, "WorkflowService")


class WorkflowService:
    """
    工作流执行业务服务层
    """

    @staticmethod
    async def verify_workflow_permissions(
        tenant_id: str,
        thread_id: UUID,
        assistant_id: UUID,
        use_cache: bool = True
    ) -> Thread:
        """
        验证工作流执行权限

        综合验证线程、租户和助理的访问权限，确保工作流可以安全执行。
        这个方法整合了线程验证、租户验证和助理验证的完整流程。

        参数:
            thread_id: 线程ID
            tenant_id: 租户ID
            assistant_id: 助理ID
            use_cache: 是否使用缓存，默认True

        返回:
            Thread: 验证通过的线程模型

        异常:
            HTTPException:
                - 404: 线程不存在
                - 403: 权限验证失败（租户不匹配或助理不属于租户）
                - 400: 助理状态无效
        """
        try:
            logger.info(f"开始验证工作流权限 - 线程: {thread_id}")

            # 1. 验证线程存在
            thread = await ThreadService.get_thread(thread_id)
            if not thread:
                logger.warning(f"线程不存在: {thread_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"线程不存在: {thread_id}"
                )

            # 2. 验证助理身份
            assistant = await AssistantService.get_assistant_by_id(
                assistant_id=assistant_id,
                use_cache=use_cache
            )

            if not assistant:
                logger.warning(f"助理不存在: assistant_id={assistant_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"助理不存在: {assistant_id}"
                )

            # 3. 验证线程数字员工租户ID匹配
            if not assistant.tenant_id == thread.tenant_id == tenant_id:
                logger.warning(f"租户不匹配: thread_id={thread_id}")
                raise HTTPException(
                    status_code=403,
                    detail="租户ID不匹配，无法访问此线程"
                )

            # 验证助理状态
            if not assistant.is_active:
                logger.warning(f"助理已被禁用: assistant_id={assistant_id}")
                raise HTTPException(
                    status_code=400,
                    detail="助理已被禁用，无法处理请求"
                )

            logger.info(f"工作流权限验证成功 - 线程: {thread_id}")
            return thread

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"验证工作流权限时发生异常: thread_id={thread_id}, 错误: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"权限验证失败: {str(e)}"
            )
