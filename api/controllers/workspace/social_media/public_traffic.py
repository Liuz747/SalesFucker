"""
社交媒体公域导流接口

该模块负责HTTP层调用，具体业务逻辑委托给服务层实现。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

<<<<<<< Updated upstream
from libs.types import MethodType
=======
from fastapi import APIRouter, HTTPException, status

from libs.types import SocialMediaActionType, MethodType
>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
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
    request: ReplyGenerationRequest, payload: dict[str, Any]
) -> list[ReplyMessageData]:
    """将模型返回转换为回复任务列表（仿制评论接口逻辑）"""
    raw_tasks = payload.get("tasks")

    # 尝试从LLM返回的tasks数组中解析
    if isinstance(raw_tasks, Iterable) and not isinstance(raw_tasks, (str, bytes)):
        tasks: list[ReplyMessageData] = []
        for index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, dict):
                continue

            # 获取任务ID
            task_id = raw_task.get("id")
            if task_id is None and index < len(request.task_list):
                task_id = request.task_list[index].id
            if task_id is None:
                task_id = str(index)

            # 解析actions
            actions = _parse_actions(raw_task.get("actions"))

            # 处理message（仿制评论逻辑）
            message = None
            if not actions:
                # 无相关性：message强制为None
                message = None
            else:
                # 有相关性：根据comment_type处理
                if request.comment_type == 1 and request.comment_prompt:
                    # 固定文案：原封不动
                    message = request.comment_prompt
                else:
                    # AI生成：使用LLM返回
                    message = raw_task.get("message")

            tasks.append(
                ReplyMessageData(
                    id=str(task_id),
                    actions=actions,
                    message=message,
                )
            )
        if tasks:
            return tasks

    # 如果LLM没有返回tasks数组，为每个请求任务创建默认响应
    return [
        ReplyMessageData(
            id=task.id,
            actions=[],
            message=None,
        )
        for task in request.task_list
    ]

>>>>>>> Stashed changes
@router.post("/comment", response_model=CommentGenerationResponse)
async def generate_comment(
    request: CommentGenerationRequest,
    service: Annotated[SocialMediaPublicTrafficService, Depends()],
):
    """生成引流评论文案"""
    try:
<<<<<<< Updated upstream
        user_prompt = service.build_comment_prompt(request)
=======
        service=SocialMediaPublicTrafficService()
        user_prompt = f"""
        生成一个针对以下内容进行回复的评论，请勿重复内容。
        平台：{request.platform}，
        产品或服务：{request.product_prompt}，
        类型：{request.comment_type}，
        {"固定文案：" if request.comment_type else "风格："}{request.comment_prompt}，
        作品内容：{request.task.product_content}
        """
>>>>>>> Stashed changes
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
