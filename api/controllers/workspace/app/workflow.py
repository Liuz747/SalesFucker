"""
工作流运行路由器

该模块提供工作流执行相关的API端点，包括同步运行、异步运行、
状态查询等功能。

端点功能:
- 同步工作流执行（等待结果）
- 异步工作流执行（后台处理）
- 运行状态查询和监控
"""

from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from models import ThreadStatus, WorkflowRun, TenantModel
from schemas.conversation_schema import MessageCreateRequest, ThreadRunResponse
from services import ThreadService, AudioService, WorkflowService
from services.suggestion_service import SuggestionService
from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from ..wraps import (
    validate_and_get_tenant,
    get_orchestrator,
    Orchestrator
)
from .background_process import BackgroundWorkflowProcessor

logger = get_component_logger(__name__, "WorkflowRouter")

# 创建工作流路由器
router = APIRouter()


@router.post("/wait", response_model=ThreadRunResponse)
async def create_run(
    thread_id: UUID,
    request: MessageCreateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)]
):
    """
    创建运行实例 - 核心工作流端点

    启动多智能体工作流处理用户输入消息。

    支持的输入格式：
    - 纯文本: {"input": "你好"}
    - 多模态: {"input": [{"type": "text", "content": "分析这个"}, {"type": "image_url", "content": "https://..."}]}
    """
    try:
        # 验证工作流权限（线程、租户、助理）
        thread = await WorkflowService.verify_workflow_permissions(
            tenant_id=tenant.tenant_id,
            assistant_id=request.assistant_id,
            thread_id=thread_id,
            use_cache=True
        )

        logger.info(f"开始运行处理 - 线程: {thread.thread_id}")

        match thread.status:
            case ThreadStatus.IDLE:
                thread.status = ThreadStatus.ACTIVE
                thread = await ThreadService.update_thread(thread)
            case ThreadStatus.ACTIVE:
                pass
            case _:
                raise HTTPException(
                    status_code=400,
                    detail=f"线程状态无效，无法处理运行请求。当前状态: {thread.status}"
                )

        # 标准化输入（处理音频转录）
        normalized_input, asr_results = await AudioService.normalize_input(request.input, str(thread.thread_id))

        # 创建工作流执行模型
        start_time = get_current_datetime()
        workflow_id = uuid4()

        workflow = WorkflowRun(
            workflow_id=workflow_id,
            thread_id=thread.thread_id,
            assistant_id=request.assistant_id,
            tenant_id=thread.tenant_id,
            input=normalized_input
        )

        # 使用编排器处理消息
        result = await orchestrator.process_conversation(workflow)

        processing_time = get_processing_time_ms(start_time)

        logger.info(f"运行处理完成 - 线程: {thread.thread_id}, 执行: {workflow_id}, 耗时: {processing_time:.2f}ms")

        # 构造 invitation
        invitation = result.business_outputs

        # 返回标准化响应
        response = ThreadRunResponse(
            run_id=workflow_id,
            thread_id=result.thread_id,
            status="completed",
            response=result.output,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            processing_time=processing_time,
            asr_results=asr_results,
            multimodal_outputs=result.multimodal_outputs if result.multimodal_outputs else None,
            invitation=invitation
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行处理失败 - 线程: {thread.thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行处理失败: {str(e)}")


@router.post("/suggestion", response_model=ThreadRunResponse)
async def create_suggestion(
    thread_id: UUID,
    request: MessageCreateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    生成回复建议
    
    根据用户输入生成3条建议回复。
    """
    try:
        # 验证工作流权限
        thread = await WorkflowService.verify_workflow_permissions(
            tenant_id=tenant.tenant_id,
            assistant_id=request.assistant_id,
            thread_id=thread_id,
            use_cache=True
        )
        
        # 标准化输入（处理音频转录并获取ASR结果）
        normalized_input, asr_results = await AudioService.normalize_input(request.input, str(thread.thread_id))

        # 生成建议
        start_time = get_current_datetime()
        suggestions_list, metrics = await SuggestionService.generate_suggestions(
            input_content=normalized_input,
            thread_id=thread_id,
            assistant_id=request.assistant_id,
            tenant_id=tenant.tenant_id
        )

        processing_time = get_processing_time_ms(start_time)

        # 生成运行ID
        run_id = uuid4()

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread.thread_id,
            status="completed",
            response=suggestions_list,
            input_tokens=metrics.get("input_tokens", 0),
            output_tokens=metrics.get("output_tokens", 0),
            processing_time=processing_time,
            asr_results=asr_results,
            multimodal_outputs=None,
            invitation=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"建议生成失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"建议生成失败: {str(e)}")


@router.post("/async")
async def create_background_run(
    thread_id: UUID,
    request: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)]
):
    """
    创建后台运行实例 - 异步工作流端点

    启动多智能体工作流在后台处理用户输入消息。

    支持的输入格式：
    - 纯文本: {"input": "你好"}
    - 多模态: {"input": [{"type": "text", "content": "分析这个"}, {"type": "image_url", "content": "https://..."}]}
    """
    try:
        # 验证工作流权限（线程、租户、助理）
        thread = await WorkflowService.verify_workflow_permissions(
            tenant_id=tenant.tenant_id,
            assistant_id=request.assistant_id,
            thread_id=thread_id,
            use_cache=True
        )

        logger.info(f"开始后台运行处理 - 线程: {thread.thread_id}")

        match thread.status:
            case ThreadStatus.IDLE:
                thread.status = ThreadStatus.ACTIVE
                thread = await ThreadService.update_thread(thread)
            case ThreadStatus.ACTIVE:
                pass
            case _:
                raise HTTPException(
                    status_code=400,
                    detail=f"线程状态无效，无法处理运行请求。当前状态: {thread.status}，需要状态: {ThreadStatus.ACTIVE}"
                )

        # 标准化输入（处理音频转录）
        normalized_input, _ = await AudioService.normalize_input(request.input, str(thread.thread_id))

        # 生成运行ID
        run_id = uuid4()
        created_at = get_current_datetime()

        # 获取后台处理器
        processor = BackgroundWorkflowProcessor()

        # 添加后台任务
        background_tasks.add_task(
            processor.process_workflow_background,
            orchestrator=orchestrator,
            run_id=run_id,
            thread_id=thread.thread_id,
            assistant_id=request.assistant_id,
            tenant_id=thread.tenant_id,
            input=normalized_input
        )

        logger.info(f"后台运行已创建 - 线程: {thread.thread_id}, 运行: {run_id}")

        # 立即返回响应
        return {
            "run_id": run_id,
            "thread_id": thread.thread_id,
            "status": "started",
            "created_at": created_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台运行创建失败 - 线程: {thread.thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"后台运行创建失败: {str(e)}")


@router.get("/{run_id}/status")
async def get_run_status(
    thread_id: UUID,
    run_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取后台运行状态
    
    查询指定运行实例的当前状态和处理进度。
    """
    try:
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

        # 返回线程状态信息
        return {
            "run_id": run_id,
            "thread_id": thread.thread_id,
            "status": thread.status,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行状态查询失败 - 线程: {thread_id}, 运行: {run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行状态查询失败: {str(e)}")
