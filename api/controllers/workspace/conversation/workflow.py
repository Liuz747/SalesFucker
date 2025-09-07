"""
工作流运行路由器

该模块提供工作流执行相关的API端点，包括同步运行、异步运行、
状态查询等功能。

端点功能:
- 同步工作流执行（等待结果）
- 异步工作流执行（后台处理）
- 运行状态查询和监控
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from controllers.dependencies import get_orchestrator_service, get_request_context
from repositories.thread_repository import ThreadRepository
from models.conversation import ThreadStatus
from .schema import MessageCreateRequest, WorkflowData
from .background_process import BackgroundWorkflowProcessor


# 依赖注入函数
async def get_thread_repository() -> ThreadRepository:
    """获取线程存储库依赖"""
    repository = ThreadRepository()
    await repository.initialize()
    return repository


logger = get_component_logger(__name__, "WorkflowRouter")

# 创建工作流路由器
router = APIRouter()


@router.post("/wait")
async def create_run(
    thread_id: str,
    request: MessageCreateRequest,
    context = Depends(get_request_context),
    repository = Depends(get_thread_repository)
):
    """
    创建运行实例 - 核心工作流端点
    
    启动多智能体工作流处理用户输入消息。这是整个系统的核心端点，
    连接前端请求与后端多智能体编排系统。
    
    工作流:
    1. 验证线程和请求有效性
    2. 通过编排器启动9智能体协同处理
    3. 返回处理结果和状态信息
    """
    try:
        # 从请求上下文获取租户ID
        tenant_id = context['tenant_id']
        logger.info(f"开始运行处理 - 线程: {thread_id}, 租户: {tenant_id}")

        # 使用依赖注入的存储库验证线程
        thread = await repository.get_thread(thread_id)
        
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
        if str(thread.metadata.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )
        
        # 调用编排器处理对话
        start_time = get_current_datetime()
        
        # 获取租户专用编排器实例
        orchestrator = get_orchestrator_service(str(tenant_id))
        
        # 使用编排器处理消息 - 这是核心工作流调用
        result = await orchestrator.process_conversation(
            customer_input=request.input.content,
            customer_id=None,  # 客户ID可以从其他地方获取，暂时设为None
            input_type="text"
        )

        workflow_data = []
        for agent_type, agent_response in result.agent_responses.items():
            workflow_data.append(
                WorkflowData(
                    type=agent_type,
                    content=agent_response
                )
            )
        
        processing_time = get_processing_time_ms(start_time)
        
        # 生成运行ID
        workflow_id = uuid.uuid4()
        
        logger.info(f"运行处理完成 - 线程: {thread_id}, 运行: {workflow_id}, 耗时: {processing_time:.2f}ms")
        
        # 返回标准化响应
        return {
            "id": workflow_id,
            "thread_id": thread_id,
            "data": workflow_data,
            "created_at": start_time,
            "processing_time": processing_time,
            # 元数据
            "metadata": {
                "tenant_id": tenant_id,
                "assistant_id": request.assistant_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行创建失败: {str(e)}")


@router.post("/async")
async def create_background_run(
    thread_id: str,
    request: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    context = Depends(get_request_context),
    repository = Depends(get_thread_repository)
):
    """
    创建后台运行实例 - 异步工作流端点
    
    启动多智能体工作流在后台处理用户输入消息。该端点立即返回运行ID，
    工作流在后台异步执行，完成后通过回调API发送结果。
    
    工作流:
    1. 验证线程和请求有效性
    2. 创建后台运行实例并立即返回
    3. 在后台启动多智能体协同处理
    4. 处理完成后调用用户指定的回调API
    """
    try:
        # 从请求上下文获取租户ID
        tenant_id = context['tenant_id']
        logger.info(f"开始后台运行处理 - 线程: {thread_id}, 租户: {tenant_id}")

        # 使用依赖注入的存储库验证线程
        thread = await repository.get_thread(thread_id)
        
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
        if str(thread.metadata.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )
        
        # 生成运行ID
        run_id = uuid.uuid4()
        created_at = get_current_datetime()

        # 获取后台处理器
        processor = BackgroundWorkflowProcessor(repository)
        
        # 添加后台任务
        background_tasks.add_task(
            processor.process_workflow_background,
            run_id=run_id,
            thread_id=thread_id,
            input=request.input,
            assistant_id=request.assistant_id,
            customer_id=None,  # 客户ID可以从其他地方获取，暂时设为None
            input_type="text"
        )
        
        logger.info(f"后台运行已创建 - 线程: {thread_id}, 运行: {run_id}")
        
        # 立即返回响应
        return {
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": request.assistant_id,
            "status": "started",
            "created_at": created_at,
            "metadata": request.metadata.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"后台运行创建失败: {str(e)}")


@router.get("/{run_id}/status")
async def get_run_status(
    thread_id: str,
    run_id: str,
    context = Depends(get_request_context),
    repository = Depends(get_thread_repository)
):
    """
    获取后台运行状态
    
    查询指定运行实例的当前状态和处理进度。
    """
    try:
        # 从请求上下文获取租户ID
        tenant_id = context['tenant_id']

        # 使用依赖注入的存储库验证线程
        thread = await repository.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )
        
        if str(thread.metadata.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=403,
                detail="租户ID不匹配，无法访问此线程"
            )
        
        # 获取线程状态（现在使用线程状态代替运行状态）
        current_thread = await repository.get_thread(thread_id)

        if not current_thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )

        # 返回线程状态信息
        return {
            "thread_id": str(current_thread.thread_id),
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