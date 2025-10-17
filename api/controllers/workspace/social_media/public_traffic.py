"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import APIRouter, HTTPException, status

from libs.types import SocialMediaActionType, MethodType
from schemas.social_media_schema import (
    CommentGenerationRequest,
    CommentGenerationResponse,
    KeywordSummaryRequest,
    KeywordSummaryResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    ReplyMessageData,
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
async def generate_comment(request: CommentGenerationRequest):
    """生成引流评论文案"""
    try:
        service = SocialMediaPublicTrafficService()
        user_prompt = f"""
        生成一个针对以下内容进行回复的评论，请勿重复内容。
        平台：{request.platform}，
        产品或服务：{request.product_prompt}，
        类型：{request.comment_type}，
        {"固定文案：" if request.comment_type else "风格："}{request.comment_prompt if request.comment_prompt else "无"}，
        作品内容：{request.task.product_content}
        """
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
async def generate_reply(request: ReplyGenerationRequest):
    """生成评论回复文案"""
    try:
        system_prompt, user_prompt = SocialMediaPublicTrafficService._build_reply_prompt(request)
        raw_response = await SocialMediaPublicTrafficService._invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=SocialMediaPublicTrafficService.DEFAULT_MAX_TOKENS,
        )
        payload = SocialMediaPublicTrafficService._parse_structured_payload(raw_response)
        tasks = _build_reply_tasks(request, payload)
        return ReplyGenerationResponse(tasks=tasks)
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
async def summarize_keywords(request: KeywordSummaryRequest):
    """评论关键词与主题摘要"""
    try:
        system_prompt, user_prompt = SocialMediaPublicTrafficService._build_summary_prompt(request)
        raw_response = await SocialMediaPublicTrafficService._invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=SocialMediaPublicTrafficService.SUMMARY_MAX_TOKENS,
        )
        payload = SocialMediaPublicTrafficService._parse_structured_payload(raw_response)
        keywords = SocialMediaPublicTrafficService._normalize_keywords(payload.get("keywords"))
        count = SocialMediaPublicTrafficService._normalize_count(payload.get("count"), len(keywords))
        summary = payload.get("summary") or "生成模型未提供摘要。"
        return KeywordSummaryResponse(keywords=keywords, count=count, summary=summary)
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
async def generate_chat_reply(request: ChatGenerationRequest):
    """生成私聊回复"""
    try:
        # 固定回复模式：直接返回chat_prompt内容
        if request.comment_type == 1 and request.chat_prompt:
            return ChatGenerationResponse(message=request.chat_prompt)

        # AI生成模式：调用LLM生成回复
        system_prompt, user_prompt = SocialMediaPublicTrafficService._build_chat_prompt(request)
        raw_response = await SocialMediaPublicTrafficService._invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=SocialMediaPublicTrafficService.DEFAULT_MAX_TOKENS,
        )
        payload = SocialMediaPublicTrafficService._parse_structured_payload(raw_response)
        message = payload.get("message") or raw_response

        return ChatGenerationResponse(message=message)
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
