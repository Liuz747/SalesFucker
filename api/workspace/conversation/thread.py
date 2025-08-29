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
from fastapi import APIRouter, HTTPException

from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from api.dependencies.orchestrator import get_orchestrator_service
from .schema import ThreadCreateRequest, MessageCreateRequest
from models import ThreadModel
from repositories.thread_repository import get_thread_repository


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter(prefix="/threads", tags=["conversation-threads"])


@router.post("")
async def create_thread(request: ThreadCreateRequest):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    start_time = get_current_datetime()
    
    try:
        # 生成线程ID
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # 创建线程数据模型
        thread = ThreadModel(
            thread_id=thread_id,
            assistant_id=request.assistant_id,
            metadata=request.metadata
        )
        
        # 获取存储库并创建线程
        repository = await get_thread_repository()
        created_thread = await repository.create_thread(thread)
        
        processing_time = get_processing_time_ms(start_time)
        
        logger.info(f"线程创建成功: {thread_id}, 耗时: {processing_time:.2f}ms")
        
        return {
            "success": True,
            "message": "线程创建成功",
            "thread_id": created_thread.thread_id,
            "tenant_id": created_thread.metadata.tenant_id,
            "conversation_status": created_thread.status,
            "created_at": created_thread.created_at,
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}")
async def get_thread(thread_id: str):
    """
    获取线程详情
    
    从数据库获取线程配置信息。
    """
    start_time = get_current_datetime()
    
    try:
        # 从存储库获取线程
        repository = await get_thread_repository()
        thread = await repository.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail=f"线程不存在: {thread_id}")
        
        processing_time = get_processing_time_ms(start_time)
        
        logger.debug(f"线程获取成功: {thread_id}, 耗时: {processing_time:.2f}ms")
        
        return {
            "success": True,
            "message": "线程获取成功",
            "data": {
                "thread_id": thread.thread_id,
                "assistant_id": thread.assistant_id,
                "status": thread.status,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at,
                "metadata": thread.metadata.model_dump()
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/runs")
async def create_run(
    thread_id: str,
    request: MessageCreateRequest
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
        logger.info(f"开始运行处理 - 线程: {thread_id}, 租户: {request.metadata.tenant_id}")
        
        # 验证租户ID存在
        if not request.metadata.tenant_id:
            raise HTTPException(
                status_code=400,
                detail="租户ID不能为空"
            )
        
        # 获取租户专用编排器实例
        orchestrator = get_orchestrator_service(request.metadata.tenant_id)
        
        # 调用编排器处理对话
        start_time = get_current_datetime()
        
        # 使用编排器处理消息 - 这是核心工作流调用
        result = await orchestrator.process_conversation(
            customer_input=request.message,
            customer_id=None,  # 客户ID可以从其他地方获取，暂时设为None
            input_type="text"
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        # 生成运行ID
        run_id = f"run_{request.metadata.tenant_id}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"运行处理完成 - 线程: {thread_id}, 运行: {run_id}, 耗时: {processing_time:.2f}ms")
        
        # 返回标准化响应
        return {
            "success": True,
            "message": "运行创建成功",
            "data": {
                "run_id": run_id,
                "thread_id": thread_id,
                "processing_time_ms": processing_time
            },
            
            # 核心运行信息
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": request.assistant_id,
            "status": "completed" if result.processing_complete else "failed",
            "created_at": start_time,
            
            # 工作流结果
            "response": result.final_response or "系统处理完成",
            "processing_complete": result.processing_complete,
            "processing_time_ms": processing_time,
            
            # 智能体响应详情
            "agent_responses": result.agent_responses,
            "agents_involved": len(result.agent_responses),
            
            # 状态和错误处理
            "error_state": result.error_state,
            "human_escalation": result.human_escalation,
            "escalation_reason": getattr(result, 'escalation_reason', None),
            
            # 元数据
            "metadata": {
                "tenant_id": request.metadata.tenant_id,
                "input_type": "text",
                "workflow_version": "v1.0"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行创建失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运行创建失败: {str(e)}")