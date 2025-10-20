"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

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
async def generate_comment(request: CommentGenerationRequest):
    """生成引流评论文案"""
    try:
        service = SocialMediaPublicTrafficService()
        user_prompt = f"""
        生成一个针对以下内容进行回复的评论。
        平台：{request.platform}，
        产品或服务：{request.product_prompt}，
        类型：{request.comment_type}，
        {"固定文案：" if request.comment_type else "风格："}{request.comment_prompt if request.comment_prompt else "无"}，
        目标作品内容：{request.task.product_content}
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
        service = SocialMediaPublicTrafficService()

        # 构建用户提示词 - 明确要求为每个评论生成对应回复
        task_descriptions = []
        for idx, task in enumerate(request.task_list, 1):
            task_descriptions.append(
                f"评论{idx} [ID: {task.id}]:\n  内容: {task.reply_content}"
            )

        user_prompt = f"""
        请对以下{len(request.task_list)}条评论分别生成回复。

        平台：{request.platform}
        产品或服务：{request.product_prompt}
        类型：{request.comment_type}
        {"固定文案：" if request.comment_type else "风格："}{request.comment_prompt if request.comment_prompt else "无"}

        评论列表：
        {chr(10).join(task_descriptions)}

        重要：请务必返回{len(request.task_list)}个任务，每个任务对应上面的一条评论，保持ID一致。
                """

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
async def summarize_keywords(request: KeywordSummaryRequest):
    """评论关键词与主题摘要"""
    try:
        service = SocialMediaPublicTrafficService()

        user_prompt = f"""
        生成社交媒体关键词和主题摘要。
        平台：{request.platform}，
        产品或服务：{request.product_prompt}，
        已存在关键词：{', '.join(request.existing_keywords) if request.existing_keywords else '无'}，
        期望生成数量：{request.expecting_count}
        """

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
async def generate_chat_reply(request: ChatGenerationRequest):
    """生成私聊回复"""
    try:
        # 固定回复模式：直接返回chat_prompt内容
        if request.comment_type == 1 and request.chat_prompt:
            return ChatGenerationResponse(message=request.chat_prompt)

        # AI生成模式：调用LLM生成回复
        service = SocialMediaPublicTrafficService()

        user_prompt = f"""
        生成私聊回复。
        平台：{request.platform}，
        产品或服务：{request.product_prompt}，
        类型：{request.comment_type}，
        {"固定文案：" if request.comment_type else "风格："}{request.chat_prompt if request.chat_prompt else "无"}，
        用户消息：{request.content}
        """

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
