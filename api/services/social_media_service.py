"""
社交媒体公域导流服务

封装与LLM的交互逻辑，供控制器调用。
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import ValidationError

from infra.runtimes import LLMClient, LLMRequest
from libs.types import Message
from schemas.social_media_schema import (
    CommentGenerationRequest,
    CommentGenerationResponse,
    ReplyGenerationRequest,
    ReplyGenerationResponse,
    KeywordSummaryRequest,
    KeywordSummaryResponse,
    KeywordSummaryData,
    SafetyFlag,
)
from utils import get_component_logger


logger = get_component_logger(__name__, "SocialMediaPublicTrafficService")


class SocialMediaServiceError(Exception):
    """社交媒体导流服务异常"""


class SocialMediaPublicTrafficService:
    """社交媒体引流文案生成服务"""

    DEFAULT_PROVIDER = "anthropic"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_MAX_TOKENS = 800

    @classmethod
    async def generate_comment(
        cls, request: CommentGenerationRequest
    ) -> CommentGenerationResponse:
        """生成评论文案"""
        try:
            system_prompt, user_prompt = cls._build_comment_prompt(request)
            raw_response = await cls._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=request.provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            payload = cls._parse_structured_payload(raw_response)
            safety_flags = cls._build_safety_flags(payload.get("safety_flags"))
            message = payload.get("message", raw_response)
            rationale = payload.get("rationale") or "生成模型未提供策略说明。"
            return CommentGenerationResponse(
                message=message,
                rationale=rationale,
                safety_flags=safety_flags,
            )
        except Exception as exc:
            logger.error("评论生成失败: %s", exc, exc_info=True)
            raise SocialMediaServiceError("评论生成失败") from exc

    @classmethod
    async def generate_reply(
        cls, request: ReplyGenerationRequest
    ) -> ReplyGenerationResponse:
        """生成评论回复文案"""
        try:
            system_prompt, user_prompt = cls._build_reply_prompt(request)
            raw_response = await cls._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=request.provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            payload = cls._parse_structured_payload(raw_response)
            safety_flags = cls._build_safety_flags(payload.get("safety_flags"))
            message = payload.get("message", raw_response)
            rationale = payload.get("rationale") or "生成模型未提供策略说明。"
            follow_up_prompt = payload.get("follow_up_prompt")
            return ReplyGenerationResponse(
                message=message,
                rationale=rationale,
                follow_up_prompt=follow_up_prompt,
                safety_flags=safety_flags,
            )
        except Exception as exc:
            logger.error("回复生成失败: %s", exc, exc_info=True)
            raise SocialMediaServiceError("回复生成失败") from exc

    @classmethod
    async def summarize_keywords(
        cls, request: KeywordSummaryRequest
    ) -> KeywordSummaryResponse:
        """生成关键词摘要"""
        try:
            system_prompt, user_prompt = cls._build_summary_prompt(request)
            raw_response = await cls._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=request.provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 1200,
            )
            payload = cls._parse_structured_payload(raw_response)
            safety_flags = cls._build_safety_flags(payload.get("safety_flags"))
            data = payload.get("data")
            if not data:
                data = {
                    "summary": payload.get("summary", raw_response),
                    "themes": payload.get("themes", []),
                    "keywords": payload.get("keywords", []),
                    "recommended_actions": payload.get("recommended_actions", []),
                }
            summary_data = KeywordSummaryData.model_validate(data)
            return KeywordSummaryResponse(
                data=summary_data,
                safety_flags=safety_flags,
            )
        except ValidationError as validation_error:
            logger.error("摘要结构校验失败: %s", validation_error, exc_info=True)
            raise SocialMediaServiceError("关键词摘要解析失败") from validation_error
        except Exception as exc:
            logger.error("关键词摘要生成失败: %s", exc, exc_info=True)
            raise SocialMediaServiceError("关键词摘要生成失败") from exc

    # ------------------------------ 内部工具方法 ------------------------------ #

    @classmethod
    async def _invoke_llm(
        cls,
        *,
        system_prompt: str,
        user_prompt: str,
        provider: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """调用统一LLM客户端"""
        client = LLMClient()
        request = LLMRequest(
            id=None,
            provider=(provider or cls.DEFAULT_PROVIDER).lower(),
            model=model or cls.DEFAULT_MODEL,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens or cls.DEFAULT_MAX_TOKENS,
        )
        response = await client.completions(request)
        return response.content

    @classmethod
    def _parse_structured_payload(cls, raw_text: str) -> dict[str, Any]:
        """解析LLM返回内容为JSON字典"""
        raw_text = raw_text.strip()
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and start < end:
                snippet = raw_text[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    logger.warning("解析LLM结果失败，返回原始文本")
        return {"message": raw_text}

    @classmethod
    def _build_safety_flags(cls, flags: Any) -> list[SafetyFlag]:
        """构造安全提示列表"""
        if not flags:
            return []
        safety_list: list[SafetyFlag] = []
        if isinstance(flags, list):
            for item in flags:
                try:
                    safety_list.append(SafetyFlag.model_validate(item))
                except ValidationError:
                    logger.warning("安全提示格式不合法，已忽略: %s", item)
        else:
            logger.warning("安全提示类型异常，已忽略: %s", flags)
        return safety_list

    @classmethod
    def _build_comment_prompt(
        cls, request: CommentGenerationRequest
    ) -> tuple[str, str]:
        """构造评论生成提示词"""
        system_prompt = (
            "你是一名擅长在社交媒体上完成公域引流的营销文案专家。"
            "请严格按照业务安全规范生成内容，避免敏感词或平台禁用表达，"
            "并使用JSON格式返回结果。"
        )

        user_parts = [
            f"目标平台: {request.platform}",
            f"原始内容摘要: {request.post_excerpt}",
        ]
        if request.campaign_goal:
            user_parts.append(f"活动目标: {request.campaign_goal}")
        if request.tone:
            user_parts.append(f"语气偏好: {request.tone}")
        if request.call_to_action:
            user_parts.append(f"行动号召: {request.call_to_action}")
        if request.audience_profile:
            user_parts.append(f"目标受众: {request.audience_profile}")
        if request.brand_guidelines:
            user_parts.append(f"品牌规范: {request.brand_guidelines}")
        if request.campaign_hook:
            user_parts.append(f"引流钩子: {request.campaign_hook}")

        user_parts.append(
            "请输出JSON，字段包括："
            "`message`(生成评论)，`rationale`(策略说明)，"
            "`safety_flags`(数组，可为空，每项含code、severity、detail)。"
        )
        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_reply_prompt(
        cls, request: ReplyGenerationRequest
    ) -> tuple[str, str]:
        """构造回复生成提示词"""
        system_prompt = (
            "你是一名社交媒体客服与引流专家，需要针对用户评论给出真诚且合规的回复。"
            "回复必须自然、鼓励进一步行动，并返回JSON结构。"
        )

        user_parts = [
            f"目标平台: {request.platform}",
            f"原评论内容: {request.parent_comment}",
        ]
        if request.parent_author:
            user_parts.append(f"原评论作者: {request.parent_author}")
        if request.sentiment:
            user_parts.append(f"原评论情绪: {request.sentiment}")
        if request.post_excerpt:
            user_parts.append(f"帖子摘要: {request.post_excerpt}")
        if request.campaign_goal:
            user_parts.append(f"活动目标: {request.campaign_goal}")
        if request.tone:
            user_parts.append(f"回复语气: {request.tone}")
        if request.call_to_action:
            user_parts.append(f"行动号召: {request.call_to_action}")
        if request.audience_profile:
            user_parts.append(f"目标受众: {request.audience_profile}")
        if request.brand_guidelines:
            user_parts.append(f"品牌规范: {request.brand_guidelines}")
        if request.comment_thread_id:
            user_parts.append(f"评论线程ID: {request.comment_thread_id}")

        user_parts.append(
            "请输出JSON，字段包括："
            "`message`(最终回复)，`rationale`(处理策略说明)，"
            "`follow_up_prompt`(可选，继续引导的问题)，"
            "`safety_flags`(数组，可为空，每项含code、severity、detail)。"
        )
        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_summary_prompt(
        cls, request: KeywordSummaryRequest
    ) -> tuple[str, str]:
        """构造关键词摘要提示词"""
        system_prompt = (
            "你是一名社交媒体舆情分析专家，负责总结评论主题并给出行动建议。"
            "请输出结构化JSON，便于自动化系统消费。"
        )

        comments_block = "\n".join(
            f"- {idx + 1}. {text}" for idx, text in enumerate(request.comments)
        )
        max_kw = request.max_keywords or 8

        user_template = (
            f"目标平台: {request.platform}\n"
            f"评论列表:\n{comments_block}\n"
            f"关键词数量上限: {max_kw}\n"
        )
        if request.campaign_goal:
            user_template += f"活动目标: {request.campaign_goal}\n"
        if request.tone:
            user_template += f"品牌语气: {request.tone}\n"
        if request.audience_profile:
            user_template += f"目标受众: {request.audience_profile}\n"
        if request.brand_guidelines:
            user_template += f"品牌规范: {request.brand_guidelines}\n"

        user_template += (
            "请输出JSON，字段`data`包含：`summary`(概述)、`themes`(主题数组)、"
            "`keywords`(关键词数组)、`recommended_actions`(建议动作数组)；"
            "`safety_flags`为数组，可为空，每项含code、severity、detail。"
        )
        return system_prompt, user_template


__all__ = ["SocialMediaPublicTrafficService", "SocialMediaServiceError"]
