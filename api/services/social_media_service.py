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
    DEFAULT_MODEL = "google/gemini-2.5-flash-preview-09-2025" #快速
    DEFAULT_TEMPERATURE = 0.5  # 温度设置为 0.5,考虑风控
    DEFAULT_MAX_TOKENS = 400  # 评论和回复生成的最大 token 数（降低以提升速度）
    SUMMARY_MAX_TOKENS = 300  # 关键词摘要的最大 token 数(更简洁)

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
        """帖子评论提示词"""
        system_prompt = """社交媒体运营专家，严格判断相关性。

任务流程：
1. 相关性判断（严格！）：产品与帖子内容是否有业务相关性？
   - 目标受众是否重叠？产品能否为帖子用户提供价值？
   - 互动数据仅作次要参考，相关性是决定性因素
   - 不相关示例：公域获客平台 vs 卖青菜 = 不相关
2. 有相关性→继续；无相关性→仅返回{"actions":[]}，不要任何其他字段

评论类型处理（仅在有相关性时）：
- type=0: AI生成，根据风格倾向创作
- type=1: 固定文案，message字段必须完全等于提供的固定内容

互动动作建议（有相关性时）：
- 必须包含多个动作组合，不要只有单一动作
- 推荐组合：[1,2,3] 或 [1,3,5] 或 [2,3,5,6] 等
- 单独的[3]是不够的，需要组合使用

输出JSON：
有相关: {"message":"文案","rationale":"原因","actions":[1,2,3]}
无相关: {"actions":[]}

动作: 1=关注 2=点赞 3=评论 4=分享 5=收藏 6=主页"""

        tasks_block = "\n".join(
            [
                f"{idx}. {task.product_content} (👍{task.likes_num} 💬{task.replies_num} ⭐{task.favorite_num} 🔄{task.forward_num})"
                for idx, task in enumerate(request.task_list, start=1)
            ]
        )

        user_parts = [
            f"平台: {request.platform}",
            f"产品: {request.product_prompt}",
            f"类型: {request.comment_type}",
        ]
        if request.comment_prompt:
            if request.comment_type == 0:
                user_parts.append(f"风格: {request.comment_prompt}")
            else:
                user_parts.append(f"固定文案(原样输出): {request.comment_prompt}")

        user_parts.append(f"\n帖子:\n{tasks_block}")

        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_reply_prompt(
        cls, request: ReplyGenerationRequest
    ) -> tuple[str, str]:
        """评论区评论提示词"""
        system_prompt = """社交媒体客服运营专家，严格判断相关性并回复用户评论。

任务流程：
1. 逐条判断每个回复内容与产品/服务的相关性（严格！）
   - 用户问题是否与产品/服务相关？能否提供有价值的回复？
   - 相关性是决定性因素
2. 有相关性→生成回复；无相关性→返回空actions

回复类型处理（仅在有相关性时）：
- type=0: AI生成，根据风格倾向创作专业回复
- type=1: 固定文案，message字段必须完全等于提供的固定内容

互动动作建议（有相关性时）：
- 必须包含多个动作组合
- 推荐组合：[1,2,3] 或 [2,3,5] 等
- 不要只有单一动作

输出JSON格式：
{
  "tasks": [
    {"id":"1","actions":[1,2,3],"message":"回复内容"},
    {"id":"2","actions":[],"message":null}
  ]
}

动作: 1=关注 2=点赞 3=评论 4=分享 5=收藏 6=主页"""

        tasks_block = "\n".join(
            [
                f"{idx}. ID={task.id} 内容: {task.reply_content}"
                for idx, task in enumerate(request.task_list, start=1)
            ]
        )

        user_parts = [
            f"平台: {request.platform}",
            f"产品: {request.product_prompt}",
            f"类型: {request.comment_type}",
        ]
        if request.comment_prompt:
            if request.comment_type == 0:
                user_parts.append(f"风格: {request.comment_prompt}")
            else:
                user_parts.append(f"固定文案(原样输出): {request.comment_prompt}")

        user_parts.append(f"\n待回复:\n{tasks_block}")

        return system_prompt, "\n".join(user_parts)

    @classmethod
    def _build_summary_prompt(
        cls, request: KeywordSummaryRequest
    ) -> tuple[str, str]:
        """关键词生成提示词"""
        system_prompt = """你是一名社交媒体关键词生成专家，根据产品/服务生成适合的营销关键词。

任务要求：
1. 根据产品描述生成适合该平台的营销关键词
2. 严格遵守去重规则：生成的关键词不能与"已有关键词"重复
3. 严格遵守数量控制：
   - expecting_count是期望的总关键词数（包含已有的）
   - 实际生成数量 = expecting_count - 已有关键词数量
   - 例如：expecting_count=6，已有4个，则只生成2个新关键词
4. 关键词应该简洁、有针对性、适合目标平台特点

输出JSON格式：
{
  "keywords": ["关键词1", "关键词2"],
  "count": 2,
  "summary": "关键词生成说明"
}"""

        existing_keywords = request.existing_keywords or []
        existing_count = len(existing_keywords)
        need_generate = max(0, request.expecting_count - existing_count)

        existing_str = ", ".join(existing_keywords) if existing_keywords else "暂无"

        user_parts = [
            f"平台: {request.platform}",
            f"产品或服务: {request.product_prompt}",
            f"期望关键词总数: {request.expecting_count}",
            f"已有关键词({existing_count}个): {existing_str}",
            f"需要生成: {need_generate}个新关键词",
            "",
            "请严格按照要求生成JSON，keywords数组中只包含新生成的关键词，不要包含已有关键词。"
        ]

        return system_prompt, "\n".join(user_parts)


__all__ = ["SocialMediaPublicTrafficService", "SocialMediaServiceError"]
