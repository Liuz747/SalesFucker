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
from core.tasks.workflows import GreetingWorkflow
from libs.factory import infra_registry
from models import Thread, ThreadStatus, TenantModel
from schemas import ThreadCreateRequest, ThreadCreateResponse
from services import ThreadService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant
from .workflow import router as workflow_router
from .analysis import router as analysis_router


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter()

router.include_router(workflow_router, prefix="/{thread_id}/runs", tags=["workflows"])
router.include_router(analysis_router, prefix="/{thread_id}", tags=["analysis"])

@router.post("", response_model=ThreadCreateResponse)
async def create_thread(
    request: ThreadCreateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    try:
        # 生成线程ID
        thread_id = request.thread_id
        
        # 创建业务模型对象
        thread = Thread(
            thread_id=thread_id,
            tenant_id=tenant.tenant_id,
            status=ThreadStatus.IDLE,
            name=request.name,
            sex=request.sex,
            age=request.age,
            phone=request.phone,
            occupation=request.occupation
        )
        
        thread_id = await ThreadService.create_thread(thread)

        temporal_client = infra_registry.get_cached_clients().temporal
        asyncio.create_task(
            temporal_client.start_workflow(
                GreetingWorkflow.run,
                thread_id,
                id=f"greeting-{thread_id}",
                task_queue=mas_config.TASK_QUEUE
            )
        )
        
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

        return {
            "thread_id": thread.thread_id,
            "tenant_id": thread.tenant_id,
            "assistant_id": thread.assistant_id,
            "status": thread.status,
            "name": thread.name,
            "sex": thread.sex,
            "age": thread.age,
            "phone": thread.phone,
            "occupation": thread.occupation,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }
        
    except Exception as e:
        logger.error(f"线程获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/record")
async def upload_record(
    thread_id: UUID,
    records: list,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    上传线程记忆记录
    
    将记忆记录存储到线程的 metadata 中，支持自动去重。
    """
    try:
        # 验证线程归属
        thread = await ThreadService.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail=f"线程不存在: {thread_id}")
            
        if thread.tenant_id != tenant.tenant_id:
            raise HTTPException(status_code=403, detail="租户ID不匹配，无法访问此线程")

        await ThreadService.update_thread_records(thread_id, records)
        
        return {"message": "记忆记录上传成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记忆记录上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
