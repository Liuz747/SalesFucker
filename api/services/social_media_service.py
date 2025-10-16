"""
社交媒体公域导流服务

封装 LLM 调用、提示词拼装和结果解析逻辑，为控制器提供复用能力。
"""

from __future__ import annotations

import json
from typing import Any

from infra.runtimes import LLMClient, LLMRequest
from libs.types import Message
from schemas.social_media_schema import (
    CommentGenerationRequest,
    ReplyGenerationRequest,
    KeywordSummaryRequest,
)
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTrafficService")


class SocialMediaServiceError(Exception):
    """社交媒体导流服务异常"""


class SocialMediaPublicTrafficService:
    """社交媒体引流文案生成服务"""

    # ------------------------------ 配置常量 ------------------------------ #
    DEFAULT_PROVIDER = "openrouter"  # 使用 OpenRouter
    DEFAULT_MODEL = "google/gemini-2.5-flash-preview-09-2025"  # 通过 OpenRouter 调用 GPT-4o-mini
    DEFAULT_TEMPERATURE = 0.7  # 温度设置为 0.7,保持创意性但不过度发散
    DEFAULT_MAX_TOKENS = 800  # 评论和回复生成的最大 token 数
    SUMMARY_MAX_TOKENS = 500  # 关键词摘要的最大 token 数(更简洁)

    # ------------------------------ 内部工具方法 ------------------------------ #

    @classmethod
    async def _invoke_llm(
        cls,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        """调用统一LLM客户端"""
        client = LLMClient()
        request = LLMRequest(
            id=None,
            provider=cls.DEFAULT_PROVIDER,
            model=cls.DEFAULT_MODEL,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ],
            temperature=cls.DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
        )
        response = await client.completions(request)
        return response.content

    @staticmethod
    def _parse_structured_payload(raw_text: str) -> dict[str, Any]:
        """解析LLM返回内容为JSON字典"""
        text = raw_text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and start < end:
                snippet = text[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    logger.warning("解析LLM结果失败，返回原始文本")
        return {"message": raw_text}

    @staticmethod
    def _normalize_keywords(value: Any) -> list[str]:
        """整理关键词输出"""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def _normalize_count(value: Any, fallback: int) -> int:
        """整理数量字段"""
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return fallback

    @classmethod
    def _build_comment_prompt(
        cls, request: CommentGenerationRequest
    ) -> tuple[str, str]:
        """构造评论生成提示词"""
        system_prompt = """你是一名熟悉社交媒体运营的营销文案专家，需要依据指定任务生成优质评论。

输出必须为JSON结构，包含以下字段：
- `message`: 生成的评论文案
- `rationale`: 文案创作理由
- `actions`: 建议用户采取的动作数组，可选值为：
  * 1: FOLLOW (关注)
  * 2: LIKE (点赞)
  * 3: COMMENT (评论)
  * 4: SHARE (分享)
  * 5: FAVORITE (收藏)
  * 6: PROFILE (查看主页)

示例输出：
{
  "message": "限时7折优惠，评论区留言抽奖送好礼！",
  "rationale": "突出限时优惠和抽奖活动，激发用户参与欲望",
  "actions": [2, 3, 5]
}"""

        tasks_block = "\n".join(
            [
                (
                    f"- 任务{idx}: {task.product_content}\n"
                    f"  指标: 点赞 {task.likes_num} / 回复 {task.replies_num} / "
                    f"收藏 {task.favorite_num} / 转发 {task.forward_num}"
                )
                for idx, task in enumerate(request.task_list, start=1)
            ]
        )

        user_parts = [
            f"平台: {request.platform}",
            f"产品或服务: {request.product_prompt}",
            f"评论类型: {request.comment_type or '未指定'}",
        ]
        if request.comment_prompt:
            user_parts.append(f"评论提示: {request.comment_prompt}")
        user_parts.append("\n候选内容列表:")
        user_parts.append(tasks_block or "- 无候选内容")
        user_parts.append("\n请严格按照上述JSON格式输出，必须包含 message、rationale 和 actions 三个字段。")
        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_reply_prompt(
        cls, request: ReplyGenerationRequest
    ) -> tuple[str, str]:
        """构造回复生成提示词"""
        system_prompt = """
            "你是一名社交媒体客服与运营专家，需要结合任务信息编写合规且具引导性的回复。"
            "输出必须为JSON结构，包含`message`、`rationale`和可选的`follow_up_prompt`字段。"
        """

        tasks_block = "\n".join(
            [
                (
                    f"- 回复任务{idx}: {task.reply_content}\n"
                    f"  附件类型: {task.file_type} | 资源: {task.file_url} | ID: {task.id}"
                )
                for idx, task in enumerate(request.task_list, start=1)
            ]
        )

        user_parts = [
            f"平台: {request.platform}",
            f"产品或服务: {request.product_prompt}",
            f"评论类型: {request.comment_type or '未指定'}",
        ]
        if request.comment_prompt:
            user_parts.append(f"评论提示: {request.comment_prompt}")
        user_parts.append("待处理评论/回复数据:")
        user_parts.append(tasks_block or "- 无待处理数据")
        user_parts.append("请返回 JSON，字段包括 message、rationale 以及可选 follow_up_prompt。")
        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_summary_prompt(
        cls, request: KeywordSummaryRequest
    ) -> tuple[str, str]:
        """构造关键词摘要提示词"""
        system_prompt = """
            "你是一名社交媒体舆情分析专家，需要根据活动目标提炼关键词并给出摘要。"
            "请使用JSON输出，包含`keywords`数组、`count`数值和`summary`文本。"
        """

        existing_keywords = ", ".join(request.existing_keywords or []) or "暂无"

        user_parts = [
            f"平台: {request.platform}",
            f"产品或服务: {request.product_prompt}",
            f"期望关键词数量: {request.expecting_count}",
            f"已有关键词: {existing_keywords}",
        ]
        if request.comment_type is not None:
            user_parts.append(f"评论类型: {request.comment_type}")
        if request.comment_prompt:
            user_parts.append(f"评论提示: {request.comment_prompt}")
        user_parts.append("请输出 JSON，包含 keywords、count 和 summary 字段。")
        return system_prompt, "\n".join(user_parts)


__all__ = ["SocialMediaPublicTrafficService", "SocialMediaServiceError"]
