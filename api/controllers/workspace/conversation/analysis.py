"""
对话分析控制器

提供生成各类对话分析结果的 API 端点，包括：
- 综合分析报告
- 用户标签
- 结构化画像
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from models import TenantModel
from services import ReportService, LabelService, ProfileService
from ..wraps import validate_and_get_tenant_id
from utils import get_component_logger

logger = get_component_logger(__name__, "AnalysisRouter")

router = APIRouter()

@router.post("/{thread_id}/report")
async def generate_thread_report(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)]
):
    """
    根据对话历史生成用户分析报告
    """
    try:
        # ReportService 现在返回包含 report_result, report_tokens, error_message 的字典
        result = await ReportService.generate_user_analysis(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        return result

    except Exception as e:
        logger.error(f"API生成报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{thread_id}/label")
async def generate_thread_labels(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)]
):
    """
    生成用户标签 (Labels)
    
    返回包含 label_result, label_tokens, error_message 的 JSON 对象。
    """
    try:
        result = await LabelService.generate_user_labels(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        return result

    except Exception as e:
        logger.error(f"API生成标签失败: {e}", exc_info=True)
        return {
            "label_result": [],
            "label_tokens": 0,
            "error_message": str(e)
        }

@router.post("/{thread_id}/profile")
async def generate_thread_profile(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)]
):
    """
    生成结构化用户画像 (Profile)
    
    返回包含 profile_result, profile_tokens, error_message 的 JSON 对象。
    """
    try:
        profile = await ProfileService.generate_user_profile(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        return profile

    except Exception as e:
        logger.error(f"API生成画像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
