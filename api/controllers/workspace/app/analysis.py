"""
对话分析控制器

提供生成各类对话分析结果的 API 端点，包括：
- 综合分析报告
- 用户标签
- 结构化画像
"""

import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from libs.exceptions import BaseHTTPException, ConversationAnalysisException
from models import TenantModel
from schemas.conversation_schema import ThreadRunResponse
from services import generate_analysis
from utils import get_component_logger, get_current_datetime, get_processing_time_ms
from ..wraps import validate_and_get_tenant

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
        # 使用通用分析服务
        result = await generate_analysis(
            run_id=run_id,
            tenant_id=tenant.tenant_id,
            thread_id=thread_id,
            analysis_type="report_generation",
            provider="bailian",
            model="qwen-plus",
            temperature=0.7
        )

        processing_time = get_processing_time_ms(start_time)

        status = "completed"
        response_content = result.get("result", "")

        # 处理错误情况
        if result.get("error_message"):
            status = "failed"
            response_content = result.get("error_message")
        # 从JSON结果中提取overall_summary字段
        elif isinstance(response_content, dict):
            response_content = response_content.get("overall_summary", "")

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            input_tokens=result.get("input_tokens"),
            output_tokens=result.get("output_tokens"),
            processing_time=processing_time
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"API生成报告失败: {e}", exc_info=True)
        raise ConversationAnalysisException(analysis_type="报告", reason=str(e))


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
        # 使用通用分析服务
        result = await generate_analysis(
            run_id=run_id,
            tenant_id=tenant.tenant_id,
            thread_id=thread_id,
            analysis_type="label_generation",
            provider="bailian",
            model="qwen3-coder-flash",
            temperature=0.7
        )

        processing_time = get_processing_time_ms(start_time)

        status = "completed"
        response_content = result.get("result", [])
        error_message = result.get("error_message")

        if error_message:
            status = "failed"
            response_content = error_message
        elif isinstance(response_content, str):
            response_content = [tag.strip() for tag in response_content.split(',') if tag.strip()]

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            input_tokens=result.get("input_tokens"),
            output_tokens=result.get("output_tokens"),
            processing_time=processing_time
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"API生成标签失败: {e}", exc_info=True)
        processing_time = get_processing_time_ms(start_time)
        raise ConversationAnalysisException(analysis_type="标签", reason=str(e)) 


@router.post("/profile", response_model=ThreadRunResponse)
async def generate_thread_profile(
    thread_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    生成结构化用户画像侧写 (Profile)

    返回包含 profile_result, profile_tokens, error_message 的 JSON 对象。
    """
    start_time = get_current_datetime()
    run_id = uuid4()

    try:
        # 使用通用分析服务
        result = await generate_analysis(
            run_id=run_id,
            tenant_id=tenant.tenant_id,
            thread_id=thread_id,
            analysis_type="profile_analysis",
            provider="bailian",
            model="qwen3-coder-flash",
            temperature=0.7
        )

        processing_time = get_processing_time_ms(start_time)

        status = "completed"
        response_content = result.get("result")
        error_message = result.get("error_message")

        if error_message:
            status = "failed"
            response_content = error_message
        elif isinstance(response_content, dict):
            extracted = response_content.get("overall_profile")
            if extracted:
                response_content = extracted
            else:
                response_content = json.dumps(response_content, ensure_ascii=False)

        return ThreadRunResponse(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            response=response_content,
            input_tokens=result.get("input_tokens"),
            output_tokens=result.get("output_tokens"),
            processing_time=processing_time
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"API生成画像失败: {e}", exc_info=True)
        processing_time = get_processing_time_ms(start_time)
        raise ConversationAnalysisException(analysis_type="画像", reason=str(e))
