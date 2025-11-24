"""
分析报告控制器

提供生成各类分析报告的 API 端点。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from models import TenantModel
from services import ReportService
from ..wraps import validate_and_get_tenant_id
from utils import get_component_logger

logger = get_component_logger(__name__, "ReportRouter")

router = APIRouter()

@router.post("/{thread_id}/report")
async def generate_thread_report(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant_id)]
):
    """
    根据对话历史生成用户分析报告
    
    - 获取线程记忆上下文
    - 分析用户画像和需求
    - 返回结构化报告
    """
    try:
        report_content = await ReportService.generate_user_analysis(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id
        )
        
        return {
            "thread_id": thread_id,
            "report": report_content
        }

    except Exception as e:
        logger.error(f"API生成报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

