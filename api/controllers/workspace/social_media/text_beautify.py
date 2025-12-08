"""
文本美化接口

该模块负责文本缩写和扩写功能的HTTP接口层。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from libs.types import TextBeautifyActionType
from schemas.social_media_schema import (
    TextBeautifyRequest,
    TextBeautifyResponse,
)
from services.social_media_service import (
    SocialMediaPublicTrafficService,
    SocialMediaServiceError,
)
from utils import get_component_logger
from ..wraps import validate_and_get_tenant, TenantModel


logger = get_component_logger(__name__, "TextBeautify")

router = APIRouter()


@router.post("/beautify", response_model=TextBeautifyResponse)
async def beautify_text(
    request: TextBeautifyRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """文本美化接口

    支持文本缩写和扩写功能：
    - action_type=1: 文本缩写
    - action_type=2: 文本扩写
    """
    try:
        logger.info(
            f"收到文本美化请求 - 租户: {tenant.tenant_id}, "
            f"类型: {request.action_type}, 文本长度: {len(request.source_text)}, "
            f"期望数量: {request.result_count}"
        )

        result = await service.text_beautify(request)

        logger.info(
            f"文本美化完成 - 运行ID: {result.run_id}, "
            f"状态: {result.status}, 结果数量: {len(result.response)}, "
            f"耗时: {result.processing_time:.2f}ms"
        )
        return result

    except SocialMediaServiceError as e:
        logger.error(f"文本美化服务错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e) or "文本美化失败，请稍后重试",
        )
    except Exception as e:
        logger.error(f"文本美化接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="文本美化失败，请稍后重试",
        )