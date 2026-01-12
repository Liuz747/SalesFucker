"""
对话处理路由器

该模块提供对话处理和管理相关的API端点，包括对话创建、消息处理、
历史查询、状态管理等功能。

端点功能:
- 对话生命周期管理（创建、处理、结束）
- 多模态消息处理（文本、语音、图像）
- 对话历史查询和导出
- 对话状态监控和分析
- 客户档案管理集成
"""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from config import mas_config
from core.tasks.workflows import ConversationPreservationWorkflow
from libs.factory import infra_registry
from models import Thread, TenantModel
from schemas import BaseResponse, ThreadPayload, ThreadCreateResponse, ThreadBatchUpdateRequest, ThreadBatchUpdateResponse
from services import ThreadService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant
from .analysis import router as analysis_router
from .workflow import router as workflow_router


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter()

router.include_router(analysis_router, prefix="/{thread_id}", tags=["analysis"])
router.include_router(workflow_router, prefix="/{thread_id}/runs", tags=["workflows"])


@router.post("", response_model=ThreadCreateResponse)
async def create_thread(
    request: ThreadPayload,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    try:
        # 创建业务模型对象
        thread = Thread(
            tenant_id=tenant.tenant_id,
            name=request.name,
            nickname=request.nickname,
            real_name=request.real_name,
            sex=request.sex,
            age=request.age,
            phone=request.phone,
            occupation=request.occupation,
            services=request.services or [],
            is_converted=request.is_converted or False
        )
        
        thread_id = await ThreadService.create_thread(thread)

        # 启动Temporal工作流
        temporal_client = infra_registry.get_cached_clients().temporal

        # 启动对话保留工作流
        task = asyncio.create_task(
            temporal_client.start_workflow(
                ConversationPreservationWorkflow.run,
                args=[thread_id, tenant.tenant_id],
                id=f"preservation-{thread_id}",
                task_queue=mas_config.TASK_QUEUE
            )
        )
        task.add_done_callback(lambda t: t.exception())

        return ThreadCreateResponse(message="线程创建成功", thread_id=thread_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}")
async def get_thread(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取线程详情
    
    从数据库获取线程配置信息。
    """
    try:
        # 使用依赖注入的存储库获取线程
        thread = await ThreadService.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(
                status_code=404, 
                detail=f"线程不存在: {thread_id}"
            )
        
        if thread.tenant_id != tenant.tenant_id:
            raise HTTPException(
                status_code=403, 
                detail="租户ID不匹配，无法访问此线程"
            )

        return thread

    except Exception as e:
        logger.error(f"线程获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/info")
async def update_thread(
    thread_id: UUID,
    request: ThreadPayload,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    更新线程客户信息

    更新线程关联的客户基本信息和消费信息。
    仅更新请求中提供的非空字段。
    """
    try:
        # 更新线程
        await ThreadService.update_thread_info(tenant.tenant_id, thread_id, request)

        return BaseResponse(message="线程更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程更新失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-update", response_model=ThreadBatchUpdateResponse)
async def batch_update_threads(
    request: ThreadBatchUpdateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    批量更新线程属性

    使用相同的字段和值更新多个线程。支持更新以下字段：
    - is_converted: 客户是否已转化
    - enable_trigger: 是否允许主动触发
    - enable_takeover: 是否允许AI接管

    特性：
    - 最多支持100个线程
    - 自动验证租户归属权限
    - 异步刷新Redis缓存
    """
    try:
        # 调用服务层批量更新
        succeeded, failed, failed_ids = await ThreadService.batch_update_threads(
            tenant_id=tenant.tenant_id,
            thread_ids=request.thread_ids,
            set_updates=request.set_updates.model_dump(exclude_unset=True)
        )

        return ThreadBatchUpdateResponse(
            message=f"批量更新完成: 成功 {succeeded} 个, 失败 {failed} 个",
            succeeded=succeeded,
            failed=failed,
            failed_ids=failed_ids
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新线程失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
