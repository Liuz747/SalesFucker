"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from fastapi import APIRouter, HTTPException, status

from schemas.social_media_schema import (
    CommentGenerationRequest,
    CommentGenerationResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    KeywordSummaryRequest,
    KeywordSummaryResponse,
)
from services.social_media_service import (
    SocialMediaPublicTrafficService,
    SocialMediaServiceError,
)
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTraffic")

router = APIRouter()


@router.post(
    "/comment",
    response_model=CommentGenerationResponse,
    status_code=status.HTTP_200_OK,
    tags=["social-media"],
)
async def generate_comment(
    request: CommentGenerationRequest,
) -> CommentGenerationResponse:
    """生成引流评论文案"""
    try:
        return await SocialMediaPublicTrafficService.generate_comment(request)
    except SocialMediaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "评论生成失败，请稍后重试",
        ) from exc
    except Exception as exc:
        logger.error("评论生成失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="评论生成失败，请稍后重试",
        ) from exc


@router.post(
    "/reply",
    response_model=ReplyGenerationResponse,
    status_code=status.HTTP_200_OK,
    tags=["social-media"],
)
async def generate_reply(request: ReplyGenerationRequest) -> ReplyGenerationResponse:
    """生成评论回复文案"""
    try:
        return await SocialMediaPublicTrafficService.generate_reply(request)
    except SocialMediaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "回复生成失败，请稍后重试",
        ) from exc
    except Exception as exc:
        logger.error("回复生成失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="回复生成失败，请稍后重试",
        ) from exc


@router.post(
    "/keywords",
    response_model=KeywordSummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["social-media"],
)
async def summarize_keywords(
    request: KeywordSummaryRequest,
) -> KeywordSummaryResponse:
    """评论关键词与主题摘要"""
    try:
        return await SocialMediaPublicTrafficService.summarize_keywords(request)
    except SocialMediaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "关键词摘要生成失败，请稍后重试",
        ) from exc
    except Exception as exc:
        logger.error("关键词摘要生成失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="关键词摘要生成失败，请稍后重试",
        ) from exc
