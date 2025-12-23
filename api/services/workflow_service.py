"""
工作流执行业务服务层
"""

from uuid import UUID

from fastapi import HTTPException

from libs.types import AccountStatus, ThreadStatus
from models import Thread
from schemas.exceptions import (
    AssistantDisabledException,
    BaseHTTPException,
    TenantValidationException,
    ThreadNotFoundException
)
from utils import get_component_logger, get_current_datetime
from .assistant_service import AssistantService
from .thread_service import ThreadService

logger = get_component_logger(__name__, "WorkflowService")


class WorkflowService:
    """
    工作流执行业务服务层
    """

    @staticmethod
    async def verify_workflow_permissions(
        tenant_id: str,
        assistant_id: UUID,
        thread_id: UUID,
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
            ThreadNotFoundException: 线程不存在
            TenantValidationException: 租户验证失败（租户不匹配或助理不属于租户）
            AssistantDisabledException: 助理已被禁用
        """
        try:
            logger.info(f"开始验证工作流权限 - 线程: {thread_id}")

            # 1. 验证线程存在
            thread = await ThreadService.get_thread(thread_id)
            if not thread:
                logger.warning(f"线程不存在: {thread_id}")
                raise ThreadNotFoundException(thread_id)

            # 2. 验证线程状态
            # 每个线程代表一个用户，拥有独立的记忆和上下文
            # 允许FAILED线程重新运行，以便用户可以从错误中恢复
            if thread.status == ThreadStatus.BUSY:
                raise HTTPException(
                    status_code=400,
                    detail=f"线程当前状态正在运行，无法处理运行请求。"
                )

            # 3. 验证助理身份
            assistant = await AssistantService.get_assistant_by_id(
                assistant_id=assistant_id,
                use_cache=use_cache
            )

            # 4. 验证线程、助理、租户ID三者匹配
            if not assistant.tenant_id == thread.tenant_id == tenant_id:
                logger.warning(f"租户、数字员工、线程不匹配: thread_id={thread_id}")
                raise TenantValidationException(tenant_id, "线程和数字员工不匹配")

            # 5. 验证助理状态
            if assistant.status != AccountStatus.ACTIVE:
                logger.warning(f"助理已被禁用: assistant_id={assistant_id}")
                raise AssistantDisabledException(assistant_id)

            # 6. 更新线程状态为BUSY，同时绑定助理ID（如果未绑定）
            update_fields = {
                "status": ThreadStatus.BUSY,
                "last_awakening_at": get_current_datetime(),
            }
            if not thread.assistant_id:
                update_fields["assistant_id"] = assistant_id

            thread = await ThreadService.update_thread_fields(thread.thread_id, update_fields)

            logger.info(f"工作流权限验证成功 - 线程: {thread_id}")
            return thread

        except BaseHTTPException:
            raise
        except Exception as e:
            logger.error(
                f"验证工作流权限时发生异常: thread_id={thread_id}, 错误: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"权限验证失败: {str(e)}"
            )
