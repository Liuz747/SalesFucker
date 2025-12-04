"""
对话分析控制器

提供生成各类对话分析结果的 API 端点，包括：
- 综合分析报告
- 用户标签
- 结构化画像
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends

from models import TenantModel
from schemas.conversation_schema import ThreadRunResponse
from services import ReportService, LabelService, ProfileService
from ..wraps import validate_and_get_tenant
from utils import get_component_logger, get_current_datetime, get_processing_time_ms

logger = get_component_logger(__name__, "AnalysisRouter")

router = APIRouter()

@router.post("/report", response_model=ThreadRunResponse)
async def generate_thread_report(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    根据对话历史生成用户分析报告
    """
    start_time = get_current_datetime()
    run_id = uuid4()
    
    try:
        # ReportService 现在返回包含 report_result, report_tokens, error_message 的字典
        result = await ReportService.generate_user_analysis(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        status = "completed"
        response_content = result.get("report_result", "")
        
        if result.get("error_message"):
            status = "failed"
            response_content = result.get("error_message")

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            processing_time=processing_time,
            metadata={"error": result.get("error_message")} if result.get("error_message") else None
        )

    except Exception as e:
        logger.error(f"API生成报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/label", response_model=ThreadRunResponse)
async def generate_thread_labels(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    生成用户标签 (Labels)
    
    返回包含 label_result, label_tokens, error_message 的 JSON 对象。
    """
    start_time = get_current_datetime()
    run_id = uuid4()

    try:
        result = await LabelService.generate_user_labels(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        status = "completed"
        response_content = result.get("label_result", [])
        
        if result.get("error_message"):
            status = "failed"
            # 如果失败，response可能是空列表或错误信息，视需求而定
            if not response_content:
                response_content = result.get("error_message")

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            processing_time=processing_time,
            metadata={"error": result.get("error_message")} if result.get("error_message") else None
        )

    except Exception as e:
        logger.error(f"API生成标签失败: {e}", exc_info=True)
        processing_time = get_processing_time_ms(start_time)
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/profile", response_model=ThreadRunResponse)
async def generate_thread_profile(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    生成结构化用户画像 (Profile)
    
    返回包含 profile_result, profile_tokens, error_message 的 JSON 对象。
    """
    start_time = get_current_datetime()
    run_id = uuid4()

    try:
        result = await ProfileService.generate_user_profile(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        status = "completed"
        response_content = result.get("profile_result")
        
        if result.get("error_message"):
            status = "failed"
            if not response_content:
                 response_content = result.get("error_message")
        
        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            processing_time=processing_time,
            metadata={"error": result.get("error_message")} if result.get("error_message") else None
        )

    except Exception as e:
        logger.error(f"API生成画像失败: {e}", exc_info=True)
        processing_time = get_processing_time_ms(start_time)
        raise HTTPException(status_code=500, detail=str(e))
