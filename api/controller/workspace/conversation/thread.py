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
import uuid
from fastapi import APIRouter, HTTPException, Depends

from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from controller.dependencies import get_orchestrator_service, get_request_context
from .schema import ThreadCreateRequest, MessageCreateRequest, ThreadModel, WorkflowData, ThreadMetadata
from repositories.thread_repository import get_thread_repository


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter(prefix="/threads", tags=["conversation-threads"])


@router.post("")
async def create_thread(
    request: ThreadCreateRequest,
    context = Depends(get_request_context)
):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    try:
        # 生成线程ID
        thread_id = request.thread_id or str(uuid.uuid4())

        # 从请求上下文获取租户ID
        tenant_id = context['tenant_id']
        
        # 创建线程数据模型
        thread = ThreadModel(
            thread_id=thread_id,
            metadata=ThreadMetadata(tenant_id=tenant_id)
        )
        
        # 获取存储库并创建线程
        repository = await get_thread_repository()
        created_thread = await repository.create_thread(thread)
        
        return {
            "thread_id": thread_id,
            "metadata": created_thread.metadata.model_dump(),
            "status": created_thread.status,
            "created_at": created_thread.created_at,
            "updated_at": created_thread.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    context = Depends(get_request_context)
):
    """
    获取线程详情
    
    从数据库获取线程配置信息。
    """
    try:
        # 从存储库获取线程
        repository = await get_thread_repository()
        thread = await repository.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(
                status_code=404, 
                detail=f"线程不存在: {thread_id}"
            )
        
        if str(thread.metadata.tenant_id) != context['tenant_id']:
            raise HTTPException(
                status_code=403, 
                detail="租户ID不匹配，无法访问此线程"
            )

        return {
            "thread_id": thread.thread_id,
            "metadata": thread.metadata.model_dump(),
            "status": thread.status,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/runs")
async def create_run(
    thread_id: str,
    request: MessageCreateRequest,
    context = Depends(get_request_context)
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
        
        # 验证线程存在且处于活跃状态
        repository = await get_thread_repository()
        thread = await repository.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"线程不存在: {thread_id}"
            )
        
        if thread.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"线程状态无效，无法处理运行请求。当前状态: {thread.status}，需要状态: active"
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
                "tenant_id": str(tenant_id),
                "assistant_id": str(request.assistant_id)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行创建失败: {str(e)}")