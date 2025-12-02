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


@router.post("/wait", response_model=ThreadRunResponse, response_model_exclude_none=True)
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
        normalized_input = await AudioService.normalize_input(request.input, str(thread.thread_id))

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

        # 计算 Token 统计
        total_input_tokens = 0
        total_output_tokens = 0
        
        
        # 从 result.values 中聚合 token 信息
        if result.values and "agent_responses" in result.values:
            agent_responses = result.values["agent_responses"]
            if isinstance(agent_responses, dict):
                for agent_resp in agent_responses.values():
                    if isinstance(agent_resp, dict):
                        token_usage = agent_resp.get("token_usage", {})
                        total_input_tokens += token_usage.get("input_tokens", 0)
                        total_output_tokens += token_usage.get("output_tokens", 0)

        # 构造 metrics
        metrics = {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "processing_time": processing_time
        }

        # 提取 ASR 结果
        # AudioService.normalize_input 会将转录文本追加到列表末尾
        # 因此 normalized_input 中超出原始 request.input 长度的部分即为 ASR 结果
        asr_results = None
        if isinstance(request.input, list) and isinstance(normalized_input, list):
            original_len = len(request.input)
            if len(normalized_input) > original_len:
                asr_results = [
                    item.content 
                    for item in normalized_input[original_len:] 
                    if hasattr(item, "content")
                ]

        # 构造 multimodal_outputs
        # 将纯文本响应也转换为 TextOutput 放入列表
        multimodal_outputs = []
        
        # 1. 添加文本响应 (如果存在)
        if result.output:
            multimodal_outputs.append({
                "type": "text",
                "text": result.output,
                "metadata": {"text_type": "response"}
            })
            
        # 2. 添加其他多模态输出
        if result.multimodal_outputs:
            for output in result.multimodal_outputs:
                 # 转换 OutputContentParams 为字典
                output_dict = {
                    "type": output.type,
                    "url": output.url, # 注意：AudioOutput需要 audio_url
                    "metadata": output.metadata
                }
                
                # 特殊字段适配
                if output.type == "audio":
                    output_dict["audio_url"] = output.url
                    # 尝试从 metadata 获取 duration 和 text
                    if output.metadata:
                        output_dict["audio_duration"] = output.metadata.get("duration", 0)
                        output_dict["audio_text"] = output.metadata.get("text", "")
                        
                elif output.type == "material":
                    output_dict["file_id"] = output.file_id if hasattr(output, "file_id") else output.url # 假设url存的是id
                    
                multimodal_outputs.append(output_dict)

        # 构造 business_outputs
        # 优先从 result.business_outputs 获取，如果没有则尝试从 appointment_intent 转换
        business_outputs = result.business_outputs
        
        if not business_outputs and result.appointment_intent:
             intent = result.appointment_intent
             if intent.get("recommendation") == "suggest_appointment":
                 # 简易映射，实际可能需要更详细的提取逻辑
                 business_outputs = {
                     "type": "appointment",
                     "status": 1, # 假设1是待确认
                     "time": 0, # 需要从 intent 中解析时间
                     "phone": "", # 需要从 intent 中解析电话
                     "name": "", 
                     "project": "",
                     "metadata": {
                         "appointment_reason": f"Intent strength: {intent.get('intent_strength')}"
                     }
                 }

        # 返回标准化响应
        response = ThreadRunResponse(
            run_id=workflow_id,
            thread_id=result.thread_id,
            status="completed",
            metrics=metrics,
            asr_results=asr_results,
            business_outputs=business_outputs,
            multimodal_outputs=multimodal_outputs,
            response=result.output # 保留兼容字段
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行处理失败 - 线程: {thread.thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行处理失败: {str(e)}")


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
        normalized_input = await AudioService.normalize_input(request.input, str(thread.thread_id))

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
