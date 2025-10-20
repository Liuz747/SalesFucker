"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from libs.types import MethodType
from schemas.social_media_schema import (
    CommentGenerationRequest,
    CommentGenerationResponse,
    KeywordSummaryRequest,
    KeywordSummaryResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    ChatGenerationRequest,
    ChatGenerationResponse,
)
from services.social_media_service import (
    SocialMediaPublicTrafficService,
    SocialMediaServiceError,
)
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTraffic")

router = APIRouter()


@router.post("/comment", response_model=CommentGenerationResponse)
async def generate_comment(
    request: CommentGenerationRequest,
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """生成引流评论文案"""
    try:
        user_prompt = service.build_comment_prompt(request)
        system_prompt = await service.load_prompt(method=MethodType.COMMENT)
        response = await service.invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=CommentGenerationResponse,
        )

        return response
    except SocialMediaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e) or "评论生成失败，请稍后重试",
        )
    except Exception as e:
        logger.error("评论生成失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="评论生成失败，请稍后重试",
        )

@router.post("/reply", response_model=ReplyGenerationResponse)
async def generate_reply(
    request: ReplyGenerationRequest,
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """生成评论回复文案"""
    try:
        user_prompt = service.build_reply_prompt(request)
        system_prompt = await service.load_prompt(method=MethodType.REPLIES)
        response = await service.invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=ReplyGenerationResponse,
        )

        return response
    except SocialMediaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e) or "回复生成失败，请稍后重试",
        )
    except Exception as e:
        logger.error("回复生成失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="回复生成失败，请稍后重试",
        )


@router.post("/keywords", response_model=KeywordSummaryResponse)
async def summarize_keywords(
    request: KeywordSummaryRequest,
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """评论关键词与主题摘要"""
    try:
        user_prompt = service.build_keywords_prompt(request)
        system_prompt = await service.load_prompt(method=MethodType.KEYWORDS)
        response = await service.invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=KeywordSummaryResponse,
        )

        return response
    except SocialMediaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e) or "关键词摘要生成失败，请稍后重试",
        )
    except Exception as e:
        logger.error("关键词摘要生成失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="关键词摘要生成失败，请稍后重试",
        )


@router.post("/chat", response_model=ChatGenerationResponse)
async def generate_chat_reply(
    request: ChatGenerationRequest,
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """生成私聊回复"""
    try:
        # 固定回复模式：直接返回chat_prompt内容
        if request.comment_type and request.chat_prompt:
            return ChatGenerationResponse(message=request.chat_prompt)

        # AI生成模式：调用LLM生成回复
        user_prompt = service.build_chat_prompt(request)
        system_prompt = await service.load_prompt(method=MethodType.PRIVATE_MESSAGE)
        response = await service.invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=ChatGenerationResponse,
        )

        return response
    except SocialMediaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e) or "私聊回复生成失败，请稍后重试",
        )
    except Exception as e:
        logger.error("私聊回复生成失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="私聊回复生成失败，请稍后重试",
        )
