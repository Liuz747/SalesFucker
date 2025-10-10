"""
工作流运行路由器

该模块提供工作流执行相关的API端点，包括同步运行、异步运行、
状态查询等功能。

端点功能:
- 同步工作流执行（等待结果）
- 异步工作流执行（后台处理）
- 运行状态查询和监控
"""

from typing import Annotated, Sequence
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from models import ThreadStatus, WorkflowRun, InputType
from services import ThreadService
from schemas.conversation_schema import MessageCreateRequest, InputContent
from core.prompts.prompts import DefaultPrompts
from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from ..wraps import (
    validate_and_get_tenant_id,
    get_orchestrator,
    TenantModel,
    Orchestrator
)
from .background_process import BackgroundWorkflowProcessor


logger = get_component_logger(__name__, "WorkflowRouter")

# 创建工作流路由器
router = APIRouter()


def _map_input_type_to_attachment_type(input_type: InputType) -> str:
    """将InputType映射到附件类型字符串"""
    mapping = {
        InputType.IMAGE: "image",
        InputType.VOICE: "audio",
        InputType.VIDEO: "video",
    }
    return mapping.get(input_type, "unknown")


def _detect_overall_input_type(content_types: set[InputType]) -> InputType:
    """从内容类型集合检测整体输入类型"""
    if not content_types:
        return InputType.TEXT

    if len(content_types) > 1:
        return InputType.MULTIMODAL

    return list(content_types)[0]


def _process_input(input_data: str | Sequence[InputContent]) -> tuple[str, list[dict] | None, InputType]:
    """
    处理输入数据，返回(text_content, attachments_data, input_type)

    Args:
        input_data: 纯文本字符串或InputContent列表

    Returns:
        元组 (文本内容, 附件数据列表, 输入类型)
    """
    if isinstance(input_data, str):
        # 纯文本输入
        return input_data, None, InputType.TEXT

    # 多模态输入 - 处理Sequence[InputContent]
    text_parts = []
    attachments_data = []
    content_types = set()

    for content in input_data:
        if content.type == InputType.TEXT:
            text_parts.append(content.content)
        else:
            # 非文本类型作为附件
            content_types.add(content.type)
            attachment_type = _map_input_type_to_attachment_type(content.type)
            attachments_data.append({
                "url": content.content,  # URL在field_validator中已验证
                "type": attachment_type,
                "source": "url"
            })

    # 确定文本内容
    if text_parts:
        text_content = " ".join(text_parts)
    else:
        # 没有文本，使用默认提示
        detected_type = _detect_overall_input_type(content_types)
        text_content = DefaultPrompts.get_prompt(detected_type)

    # 检测整体输入类型
    input_type = _detect_overall_input_type(content_types) if attachments_data else InputType.TEXT

    return text_content, attachments_data if attachments_data else None, input_type


@router.post("/wait")
async def create_run(
    thread_id: UUID,
    request: MessageCreateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)],
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)]
):
    """
    创建运行实例 - 核心工作流端点

    启动多智能体工作流处理用户输入消息。这是整个系统的核心端点，
    连接前端请求与后端多智能体编排系统。

    支持的请求格式：
    1. {"input": "你好"}  # 纯文本
    2. {"input": [{"type": "text", "content": "分析这个"}, {"type": "image_url", "content": "https://..."}]}  # 多模态
    3. {"input": [{"type": "image_url", "content": "https://..."}]}  # 纯附件（使用默认提示）
    """
    try:
        logger.info(f"开始运行处理 - 线程: {thread_id}, 租户: {tenant.tenant_id}")

        thread = await ThreadService.get_thread(thread_id)

        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )

        if thread.status != ThreadStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail=f"线程状态无效，无法处理运行请求。当前状态: {thread.status}，需要状态: {ThreadStatus.ACTIVE}"
            )

        # 验证线程租户ID匹配
        if thread.metadata.tenant_id != tenant.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )

        # 处理输入（纯文本或多模态）
        text_content, attachments_data, input_type = _process_input(request.input)
        logger.info(f"输入处理完成 - 类型: {input_type}, 附件数: {len(attachments_data) if attachments_data else 0}")
        logger.debug(f"文本内容: {text_content[:100]}..." if len(text_content) > 100 else f"文本内容: {text_content}")

        # 创建工作流执行模型
        start_time = get_current_datetime()
        workflow_id = uuid4()

        workflow = WorkflowRun(
            workflow_id=workflow_id,
            thread_id=thread_id,
            assistant_id=request.assistant_id,
            tenant_id=tenant.tenant_id,
            input=text_content,  # 使用确定的文本内容
            attachments=attachments_data,  # 包含下载后的本地路径
            type=input_type  # 自动检测的类型
        )

        # 使用编排器处理消息
        result = await orchestrator.process_conversation(workflow)

        processing_time = get_processing_time_ms(start_time)

        logger.info(f"运行处理完成 - 线程: {thread_id}, 执行: {workflow_id}, 耗时: {processing_time:.2f}ms")

        # 返回标准化响应
        return {
            "id": result.workflow_id,
            "thread_id": result.thread_id,
            "data": {
                "input": result.input,
                "output": result.output,
                "total_tokens": result.total_tokens
            },
            "created_at": start_time,
            "processing_time": processing_time,
            # 元数据
            "metadata": {
                "tenant_id": result.tenant_id,
                "assistant_id": result.assistant_id,
                "workflow_id": str(result.workflow_id),
                "input_type": input_type,
                "has_attachments": attachments_data is not None,
                "attachment_count": len(attachments_data) if attachments_data else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行创建失败: {str(e)}")


@router.post("/async")
async def create_background_run(
    thread_id: UUID,
    request: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)],
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)]
):
    """
    创建后台运行实例 - 异步工作流端点

    启动多智能体工作流在后台处理用户输入消息。该端点立即返回运行ID，
    工作流在后台异步执行，完成后通过回调API发送结果。

    支持的请求格式：
    1. {"input": "你好"}  # 纯文本
    2. {"input": [{"type": "text", "content": "分析这个"}, {"type": "image_url", "content": "https://..."}]}  # 多模态
    3. {"input": [{"type": "image_url", "content": "https://..."}]}  # 纯附件（使用默认提示）
    """
    try:
        logger.info(f"开始后台运行处理 - 线程: {thread_id}, 租户: {tenant.tenant_id}")

        thread = await ThreadService.get_thread(thread_id)

        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )

        if thread.status != ThreadStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail=f"线程状态无效，无法处理运行请求。当前状态: {thread.status}，需要状态: {ThreadStatus.ACTIVE}"
            )

        # 验证线程租户ID匹配
        if thread.metadata.tenant_id != tenant.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )

        # 处理输入（纯文本或多模态）
        text_content, attachments_data, input_type = _process_input(request.input)
        logger.info(f"输入处理完成 - 类型: {input_type}, 附件数: {len(attachments_data) if attachments_data else 0}")

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
            thread_id=thread_id,
            input_content=text_content,
            attachments=attachments_data,
            assistant_id=request.assistant_id,
            tenant_id=tenant.tenant_id,
            input_type=input_type
        )

        logger.info(f"后台运行已创建 - 线程: {thread_id}, 运行: {run_id}")

        # 立即返回响应
        return {
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": request.assistant_id,
            "status": "started",
            "created_at": created_at,
            "metadata": {
                **(request.metadata.model_dump() if request.metadata else {}),
                "input_type": input_type,
                "has_attachments": attachments_data is not None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"后台运行创建失败: {str(e)}")


@router.get("/{run_id}/status")
async def get_run_status(
    thread_id: UUID,
    run_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)]
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
        
        if thread.metadata.tenant_id != tenant.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )
        
        # 获取线程状态（现在使用线程状态代替运行状态）
        current_thread = await ThreadService.get_thread(thread_id)

        if not current_thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )

        # 返回线程状态信息
        return {
            "thread_id": current_thread.thread_id,
            "status": current_thread.status,
            "created_at": current_thread.created_at,
            "updated_at": current_thread.updated_at,
            "run_id": run_id,  # 保持向后兼容性
            "metadata": current_thread.metadata.model_dump()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行状态查询失败 - 线程: {thread_id}, 运行: {run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行状态查询失败: {str(e)}")