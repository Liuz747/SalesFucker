"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import APIRouter, HTTPException, status

from libs.types import SocialMediaActionType
from schemas.social_media_schema import (
    CommentGenerationRequest,
    CommentGenerationResponse,
    KeywordSummaryRequest,
    KeywordSummaryResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    ReplyMessageData,
)
from services.social_media_service import (
    SocialMediaPublicTrafficService,
    SocialMediaServiceError,
)
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTraffic")

router = APIRouter()


def _parse_actions(raw: Any) -> list[SocialMediaActionType]:
    """将任意输入转换成动作类型枚举列表"""

    def _coerce_single(value: Any) -> SocialMediaActionType | None:
        if isinstance(value, SocialMediaActionType):
            return value
        if isinstance(value, str):
            upper_value = value.upper()
            if upper_value in SocialMediaActionType.__members__:
                return SocialMediaActionType[upper_value]
            try:
                value = int(value)
            except ValueError:
                return None
        try:
            return SocialMediaActionType(int(value))
        except (TypeError, ValueError):
            logger.debug("忽略无法解析的动作类型值: %r", value)
            return None

    if raw is None:
        return []
    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        actions = [_coerce_single(item) for item in raw]
        return [action for action in actions if action is not None]

    action = _coerce_single(raw)
    return [action] if action is not None else []


def _build_reply_tasks(
    request: ReplyGenerationRequest, payload: dict[str, Any], fallback_message: str
) -> list[ReplyMessageData]:
    """将模型返回转换为回复任务列表"""
    raw_tasks = payload.get("tasks")
    if isinstance(raw_tasks, Iterable) and not isinstance(raw_tasks, (str, bytes)):
        tasks: list[ReplyMessageData] = []
        for index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, dict):
                continue
            task_id = raw_task.get("id")
            if task_id is None and index < len(request.task_list):
                task_id = request.task_list[index].id
            if task_id is None:
                task_id = str(index)
            actions = _parse_actions(raw_task.get("actions"))
            message = raw_task.get("message") or fallback_message
            tasks.append(
                ReplyMessageData(
                    id=str(task_id),
                    actions=actions,
                    message=message,
                )
            )
        if tasks:
            return tasks

    actions = _parse_actions(payload.get("actions"))
    return [
        ReplyMessageData(
            id=task.id,
            actions=actions,
            message=fallback_message,
        )
        for task in request.task_list
    ]


@router.post("/comment", response_model=CommentGenerationResponse)
async def generate_comment(request: CommentGenerationRequest):
    """生成引流评论文案"""
    try:
        system_prompt, user_prompt = SocialMediaPublicTrafficService._build_comment_prompt(request)
        raw_response = await SocialMediaPublicTrafficService._invoke_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=SocialMediaPublicTrafficService.DEFAULT_MAX_TOKENS,
        )
        payload = SocialMediaPublicTrafficService._parse_structured_payload(raw_response)
        message = payload.get("message") or raw_response
        actions = _parse_actions(payload.get("actions"))
        return CommentGenerationResponse(actions=actions, message=message)
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
        message = payload.get("message") or raw_response
        tasks = _build_reply_tasks(request, payload, message)
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
