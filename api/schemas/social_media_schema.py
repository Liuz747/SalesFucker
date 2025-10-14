"""
社交媒体公域导流数据模型

定义请求与响应Schema，供FastAPI控制器及服务层复用。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class SocialPlatform(StrEnum):
    """支持的社交媒体平台枚举"""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    REDDIT = "reddit"
    LINKEDIN = "linkedin"
    OTHER = "other"


class SafetySeverity(StrEnum):
    """安全提示严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetyFlag(BaseModel):
    """安全合规提示"""

    code: str = Field(..., description="提示编码")
    severity: SafetySeverity = Field(..., description="严重程度")
    detail: str = Field(..., description="提示详情")


class BaseGenerationRequest(BaseModel):
    """通用生成请求基础字段"""

    platform: SocialPlatform = Field(..., description="社交媒体平台")
    tone: Optional[str] = Field(None, description="期望的语气风格")
    campaign_goal: Optional[str] = Field(None, description="活动目标，例如拉新、转化等")
    call_to_action: Optional[str] = Field(None, description="引导至私域的行动号召")
    audience_profile: Optional[str] = Field(None, description="目标受众画像")
    brand_guidelines: Optional[str] = Field(None, description="品牌调性或话术规范")
    provider: Optional[str] = Field(None, description="指定LLM供应商")
    model: Optional[str] = Field(None, description="指定模型")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="采样温度")
    max_tokens: Optional[int] = Field(
        None, ge=64, le=2048, description="生成的最大token数"
    )


class CommentGenerationRequest(BaseGenerationRequest):
    """评论生成请求"""

    post_excerpt: str = Field(..., min_length=10, description="原帖子/视频核心内容摘要")
    campaign_hook: Optional[str] = Field(
        None, description="计划使用的引流钩子或福利信息"
    )


class CommentGenerationResponse(BaseModel):
    """评论生成响应"""

    message: str = Field(..., description="生成的评论文案")
    rationale: str = Field(..., description="文案设计思路")
    safety_flags: list[SafetyFlag] = Field(default_factory=list, description="安全提示")


class ReplyGenerationRequest(BaseGenerationRequest):
    """评论回复请求"""

    parent_comment: str = Field(..., min_length=5, description="需要回复的原评论内容")
    parent_author: Optional[str] = Field(None, description="原评论发布者昵称")
    sentiment: Optional[str] = Field(None, description="原评论情绪研判")
    comment_thread_id: Optional[str] = Field(
        None, description="平台侧评论线程标识，便于运营追踪"
    )
    post_excerpt: Optional[str] = Field(None, description="帖子关键信息")


class ReplyGenerationResponse(BaseModel):
    """评论回复响应"""

    message: str = Field(..., description="生成的回复文案")
    rationale: str = Field(..., description="回复策略说明")
    follow_up_prompt: Optional[str] = Field(
        None, description="建议引导用户进一步互动的问题或行动"
    )
    safety_flags: list[SafetyFlag] = Field(default_factory=list, description="安全提示")


class KeywordSummaryRequest(BaseGenerationRequest):
    """关键词摘要请求"""

    comments: list[str] = Field(..., min_length=1, description="评论或回复列表")
    max_keywords: Optional[int] = Field(
        None, ge=3, le=20, description="希望提炼的关键词数量上限"
    )

    @model_validator(mode="after")
    def validate_comments_payload(self) -> "KeywordSummaryRequest":
        """确保评论数量与长度在合理范围内"""
        comment_count = len(self.comments)
        if comment_count > 50:
            raise ValueError("单次最多支持分析50条评论")
        for item in self.comments:
            if len(item) > 800:
                raise ValueError("单条评论长度不能超过800字符")
        return self


class KeywordSummaryData(BaseModel):
    """摘要数据模型"""

    summary: str = Field(..., description="整体舆情摘要")
    themes: list[str] = Field(default_factory=list, description="主要主题列表")
    keywords: list[str] = Field(default_factory=list, description="提炼的关键词")
    recommended_actions: list[str] = Field(
        default_factory=list, description="建议采取的运营动作"
    )


class KeywordSummaryResponse(BaseModel):
    """关键词摘要响应"""

    data: KeywordSummaryData = Field(..., description="结构化摘要数据")
    safety_flags: list[SafetyFlag] = Field(default_factory=list, description="安全提示")


__all__ = [
    "SocialPlatform",
    "SafetySeverity",
    "SafetyFlag",
    "CommentGenerationRequest",
    "CommentGenerationResponse",
    "ReplyGenerationRequest",
    "ReplyGenerationResponse",
    "KeywordSummaryRequest",
    "KeywordSummaryResponse",
    "KeywordSummaryData",
]
