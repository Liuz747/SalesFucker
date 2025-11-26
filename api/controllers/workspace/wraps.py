"""
租户验证依赖

提供端点级别的租户验证依赖，确保安全的多租户隔离。
每个端点可以独立控制是否需要租户验证。

核心功能:
- 装饰器模式的租户验证
- Redis缓存优化的验证性能
- 细粒度的端点访问控制
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, Path, Depends, Body

from core.app.orchestrator import Orchestrator
from models import Thread, TenantModel
from services.tenant_service import TenantService
from services.thread_service import ThreadService
from services.assistant_service import AssistantService
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantValidation")


async def validate_and_get_tenant(request: Request) -> Optional[TenantModel]:
    """依赖注入函数 - 租户验证"""
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "TENANT_ID_REQUIRED",
                "message": "请求必须包含租户ID",
                "methods": "Header: X-Tenant-ID"
            }
        )
    
    try:
        tenant = await TenantService.query_tenant(tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "TENANT_NOT_FOUND",
                    "message": f"租户 {tenant_id} 不存在"
                }
            )
        
        if not tenant.is_active:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "TENANT_DISABLED", 
                    "message": f"租户 {tenant_id} 已被禁用"
                }
            )
        
        return tenant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail="租户验证失败")


async def get_orchestrator(request: Request):
    """
    Lazy loading（并缓存）编排器实例。
    - 仅在首次被工作流端点请求时创建
    - 实例存放于 app.state，供后续请求复用
    """
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        orchestrator = Orchestrator()
        request.app.state.orchestrator = orchestrator
    try:
        yield orchestrator
    finally:
        pass


async def validate_workflow_permissions(
    thread_id: UUID = Path(description="线程ID"),
    assistant_id: UUID = Body(embed=True),
    tenant: TenantModel = Depends(validate_and_get_tenant)
) -> Thread:
    """
    工作流权限验证依赖注入函数

    专为工作流端点设计的综合权限验证，包括：
    - 线程存在性验证
    - 租户权限验证
    - 助理身份验证
    - 助理状态验证

    参数:
        thread_id: 路径参数 - 线程ID
        assistant_id: 请求体参数 - 助理ID
        tenant: 依赖注入 - 已验证的租户模型

    返回:
        Thread: 验证通过的线程模型

    异常:
        HTTPException:
            - 404: 线程或助理不存在
            - 403: 权限验证失败（租户不匹配或助理不属于租户）
            - 400: 助理状态无效
    """
    try:
        logger.info(f"开始验证工作流权限 - 线程: {thread_id}, 助理: {assistant_id}")

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
            use_cache=True
        )

        if not assistant:
            logger.warning(f"助理不存在: assistant_id={assistant_id}")
            raise HTTPException(
                status_code=404,
                detail=f"助理不存在: {assistant_id}"
            )

        # 3. 验证线程、助理、租户ID三者匹配
        if not assistant.tenant_id == thread.tenant_id == tenant.tenant_id:
            logger.warning(f"租户、数字员工、线程不匹配: thread_id={thread_id}")
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )

        # 4. 验证助理状态
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
        logger.error(f"验证工作流权限时发生异常: thread_id={thread_id}, 错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"权限验证失败: {str(e)}"
        )
