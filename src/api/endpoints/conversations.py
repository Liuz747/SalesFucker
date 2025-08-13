"""
对话处理API端点

该模块提供对话处理和管理相关的API端点，包括对话创建、消息处理、
历史查询、状态管理等功能。

端点功能:
- 对话生命周期管理（创建、处理、结束）
- 多模态消息处理（文本、语音、图像）
- 对话历史查询和导出
- 对话状态监控和分析
- 客户档案管理集成
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging

from src.api.dependencies.orchestrator import get_orchestrator_service
from src.api.dependencies.request_context import get_request_context
from src.api.dependencies.devices import get_device_client
from src.auth.jwt_auth import get_service_context
from src.auth.models import ServiceContext
from ..schemas.conversations import (
    ConversationRequest,
    ConversationStartRequest,
    ConversationHistoryRequest,
    ConversationExportRequest,
    ConversationResponse,
    ConversationStartResponse,
    ConversationStatusResponse,
    ConversationHistoryResponse,
    ConversationAnalyticsResponse,
    ConversationExportResponse,
    ConversationStatus,
    InputType
)
from ..schemas.requests import PaginationRequest
from ..exceptions import (
    ConversationException,
    ValidationException,
    ProcessingException
)
from ..handlers.conversation_handler import ConversationHandler
from src.utils import get_component_logger

logger = get_component_logger(__name__, "ConversationEndpoints")

# 创建路由器
router = APIRouter(prefix="/chat", tags=["chat"])

# 创建处理器实例
conversation_handler = ConversationHandler()


@router.post("/new", response_model=ConversationStartResponse)
async def start_conversation(
    request: ConversationStartRequest,
    service: ServiceContext = Depends(get_service_context),
    context: Dict[str, Any] = Depends(get_request_context),
    orchestrator = Depends(get_orchestrator_service),
    device_client = Depends(get_device_client)
):
    """
    开始新对话
    
    创建新的对话会话，初始化相关智能体，加载客户档案。
    """
    try:
        # 使用请求中的tenant_id进行数据隔离
        # (在信任模型下，后端服务负责提供正确的tenant_id)
        
        # 验证设备存在
        device_info = await device_client.get_device(request.device_id, request.tenant_id)
        if not device_info:
            raise HTTPException(
                status_code=404,
                detail=f"设备 {request.device_id} 不存在或不属于租户 {request.tenant_id}"
            )
        
        return await conversation_handler.start_conversation(
            request=request,
            context=context,
            orchestrator=orchestrator
        )
        
    except Exception as e:
        logger.error(f"开始对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/message", response_model=ConversationResponse)
async def process_message(
    thread_id: str,
    request: ConversationRequest,
    service: ServiceContext = Depends(get_service_context),
    context: Dict[str, Any] = Depends(get_request_context),
    orchestrator = Depends(get_orchestrator_service),
    device_client = Depends(get_device_client)
):
    """
    处理对话消息
    
    通过完整的9智能体多智能体系统处理客户消息，支持多模态输入。
    """
    try:
        # 使用请求中的tenant_id进行数据隔离
        # (在信任模型下，后端服务负责提供正确的tenant_id)
        
        # 验证设备存在
        device_info = await device_client.get_device(request.device_id, request.tenant_id)
        if not device_info:
            raise HTTPException(
                status_code=404,
                detail=f"设备 {request.device_id} 不存在或不属于租户 {request.tenant_id}"
            )
        
        return await conversation_handler.process_message(
            request=request,
            context=context,
            thread_id=thread_id,
            orchestrator=orchestrator
        )
        
    except Exception as e:
        logger.error(f"消息处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/status", response_model=ConversationStatusResponse)
async def get_conversation_status(
    thread_id: str,
    service: ServiceContext = Depends(get_service_context),
    include_details: bool = Query(False, description="是否包含详细信息")
):
    """
    获取对话状态
    
    返回指定对话的当前状态、统计信息和性能指标。
    """
    try:
        return await conversation_handler.get_conversation_status(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            include_details=include_details
        )
        
    except Exception as e:
        logger.error(f"获取对话状态失败 {thread_id}: {e}", exc_info=True)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="对话不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/end")
async def end_conversation(
    thread_id: str,
    reason: Optional[str] = Query(None, description="结束原因"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    结束对话
    
    正常结束对话会话，保存对话记录并更新客户档案。
    """
    try:
        return await conversation_handler.end_conversation(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            reason=reason
        )
        
    except Exception as e:
        logger.error(f"结束对话失败 {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    service: ServiceContext = Depends(get_service_context),
    customer_id: Optional[str] = Query(None, description="客户ID"),
    thread_id: Optional[str] = Query(None, description="对话ID"),
    status: Optional[ConversationStatus] = Query(None, description="对话状态"),
    input_type: Optional[InputType] = Query(None, description="输入类型"),
    pagination: PaginationRequest = Depends(),
    include_messages: bool = Query(True, description="是否包含消息内容"),
    include_agent_responses: bool = Query(False, description="是否包含智能体响应")
):
    """
    查询对话历史
    
    支持多种筛选条件查询历史对话记录。
    """
    try:
        history_request = ConversationHistoryRequest(
            customer_id=customer_id,
            thread_id=thread_id,
            status=status,
            input_type=input_type,
            include_messages=include_messages,
            include_agent_responses=include_agent_responses
        )
        
        return await conversation_handler.get_conversation_history(
            request=history_request,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"查询对话历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/messages")
async def get_conversation_messages(
    thread_id: str,
    service: ServiceContext = Depends(get_service_context),
    pagination: PaginationRequest = Depends(),
    include_attachments: bool = Query(False, description="是否包含附件信息"),
    include_analysis: bool = Query(False, description="是否包含分析结果")
):
    """
    获取对话消息详情
    
    返回指定对话的所有消息记录，支持分页和详细信息选项。
    """
    try:
        return await conversation_handler.get_conversation_messages(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            pagination=pagination,
            include_attachments=include_attachments,
            include_analysis=include_analysis
        )
        
    except Exception as e:
        logger.error(f"获取对话消息失败 {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=ConversationAnalyticsResponse)
async def get_conversation_analytics(
    service: ServiceContext = Depends(get_service_context),
    days: int = Query(30, ge=1, le=365, description="分析天数"),
    customer_id: Optional[str] = Query(None, description="指定客户ID"),
    agent_type: Optional[str] = Query(None, description="指定智能体类型")
):
    """
    获取对话分析报告
    
    提供对话统计、性能分析、趋势数据和智能体表现分析。
    """
    try:
        return await conversation_handler.get_conversation_analytics(
            tenant_id=request.tenant_id,
            days=days,
            customer_id=customer_id,
            agent_type=agent_type
        )
        
    except Exception as e:
        logger.error(f"获取对话分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export", response_model=ConversationExportResponse)
async def export_conversations(
    request: ConversationExportRequest,
    background_tasks: BackgroundTasks,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    导出对话记录
    
    支持多种格式导出对话记录，包括JSON、CSV、Excel和PDF格式。
    """
    try:
        # JWT认证中已验证租户身份，无需重复检查
        
        return await conversation_handler.export_conversations(
            request=request,
            background_tasks=background_tasks
        )
        
    except Exception as e:
        logger.error(f"导出对话记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 客户相关端点

@router.get("/customer/{customer_id}")
async def get_customer_conversations(
    customer_id: str,
    service: ServiceContext = Depends(get_service_context),
    pagination: PaginationRequest = Depends(),
    status: Optional[ConversationStatus] = Query(None, description="对话状态筛选")
):
    """
    获取客户的所有对话
    
    返回指定客户的历史对话记录，支持状态筛选和分页。
    """
    try:
        return await conversation_handler.get_customer_conversations(
            customer_id=customer_id,
            tenant_id=request.tenant_id,
            pagination=pagination,
            status=status
        )
        
    except Exception as e:
        logger.error(f"获取客户对话失败 {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customer/{customer_id}/summary")
async def get_customer_conversation_summary(
    customer_id: str,
    service: ServiceContext = Depends(get_service_context),
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """
    获取客户对话摘要
    
    返回客户对话的统计摘要，包括对话次数、满意度、主要话题等。
    """
    try:
        return await conversation_handler.get_customer_summary(
            customer_id=customer_id,
            tenant_id=request.tenant_id,
            days=days
        )
        
    except Exception as e:
        logger.error(f"获取客户摘要失败 {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 实时监控端点

@router.get("/active")
async def get_active_conversations(
    service: ServiceContext = Depends(get_service_context),
    pagination: PaginationRequest = Depends()
):
    """
    获取活跃对话列表
    
    返回当前正在进行的对话会话。
    """
    try:
        return await conversation_handler.get_active_conversations(
            tenant_id=request.tenant_id,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"获取活跃对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/real-time")
async def get_realtime_metrics(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    获取实时指标
    
    返回对话处理的实时性能指标和统计数据。
    """
    try:
        return await conversation_handler.get_realtime_metrics(
            tenant_id=tenant_context.tenant_id
        )
        
    except Exception as e:
        logger.error(f"获取实时指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 管理端点

@router.post("/{thread_id}/escalate")
async def escalate_conversation(
    thread_id: str,
    reason: str = Query(description="升级原因"),
    priority: str = Query("normal", description="优先级", pattern="^(low|normal|high|urgent)$"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    升级对话到人工处理
    
    将对话标记为需要人工介入，并通知相关人员。
    """
    try:
        return await conversation_handler.escalate_conversation(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            reason=reason,
            priority=priority
        )
        
    except Exception as e:
        logger.error(f"对话升级失败 {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/feedback")
async def submit_conversation_feedback(
    thread_id: str,
    rating: int = Query(ge=1, le=5, description="评分（1-5）"),
    feedback: Optional[str] = Query(None, description="反馈内容"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    提交对话反馈
    
    收集客户对对话质量的评价和反馈。
    """
    try:
        return await conversation_handler.submit_feedback(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            rating=rating,
            feedback=feedback
        )
        
    except Exception as e:
        logger.error(f"提交反馈失败 {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{thread_id}")
async def delete_conversation(
    thread_id: str,
    service: ServiceContext = Depends(get_service_context),
    permanent: bool = Query(False, description="是否永久删除")
):
    """
    删除对话记录
    
    软删除或永久删除指定的对话记录。
    """
    try:
        return await conversation_handler.delete_conversation(
            thread_id=thread_id,
            tenant_id=request.tenant_id,
            permanent=permanent
        )
        
    except Exception as e:
        logger.error(f"删除对话失败 {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))