"""
营销计划生成路由器

该模块提供营销计划生成的API端点，允许用户基于业务背景生成
营销策略或内容营销计划。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from core.agents import MarketingAgent
from libs.exceptions import BaseHTTPException, MarketingPlanGenerationException
from models import TenantModel
from schemas.marketing_schema import MarketingPlanRequest, MarketingPlanResponse
from utils import get_component_logger, get_current_datetime, get_processing_time
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__, "MarketingRouter")

# 创建营销路由器
router = APIRouter()


@router.post("/marketing/plans", response_model=MarketingPlanResponse)
async def create_marketing_plan(
    request: MarketingPlanRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    生成营销计划

    基于提供的业务背景和约束条件，生成包含自然语言分析和3个结构化方案选项的营销计划。

    返回：
    - response: 营销专家的自然语言分析
    - options: 3个结构化的营销方案
    """
    try:
        logger.info(f"开始生成营销计划 - tenant: {tenant.tenant_id}")

        start_time = get_current_datetime()

        # 实例化营销智能体
        marketing_agent = MarketingAgent()

        # 生成营销计划
        response = await marketing_agent.generate_marketing_plans(
            request=request,
            tenant_id=tenant.tenant_id
        )

        processing_time = get_processing_time(start_time)

        logger.info(
            f"营销计划生成完成 - tenant: {tenant.tenant_id}, "
            f"options: {len(response.options)}, "
            f"tokens: {response.input_tokens} + {response.output_tokens}, "
            f"耗时: {processing_time:.2f}s"
        )

        # 构造响应
        response.processing_time = round(processing_time, 2)

        return response

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"营销计划生成失败: {e}", exc_info=True)
        raise MarketingPlanGenerationException(str(e))
