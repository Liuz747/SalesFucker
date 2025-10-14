"""
社交媒体公域导流数据模型

定义请求与响应Schema，供FastAPI控制器及服务层复用。
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class SocialPlatform(StrEnum):
    """支持的社交媒体平台枚举"""

    REDNOTE = "rednote"
    DOUYING = "douyin"


class CommentData(BaseModel):
    """评论模型"""

    product_content: str = Field(description="评论内容")
    likes_num: int = Field(description="点赞数")
    replies_num: int = Field(description="回复数")
    favorite_num: int = Field(description="收藏数")
    forward_num: int = Field(description="转发数")


class ReplyData(BaseModel):
    """回复模型"""

    id: str = Field(description="回复ID")
    file_type: str = Field(description="文件类型")
    file_url: str = Field(description="文件URL")
    reply_content: str = Field(description="回复内容")


class BaseGenerationRequest(BaseModel):
    """通用生成请求基础字段"""

    platform: SocialPlatform = Field(description="社交媒体平台")
    goal_prompt: str = Field(description="活动目标，例如拉新、转化等")
    comment_type: Optional[int] = Field(None, description="评论类型，如1-5级")
    comment_prompt: Optional[str] = Field(None, description="评论内容")


class CommentGenerationRequest(BaseGenerationRequest):
    """评论生成请求"""

    task_list: Sequence[CommentData] = Field(description="任务列表")


class CommentGenerationResponse(BaseModel):
    """评论生成响应"""

    message: str = Field(description="生成的评论文案")
    rationale: str = Field(description="文案设计思路")


class ReplyGenerationRequest(BaseGenerationRequest):
    """评论回复请求"""

    task_list: Sequence[ReplyData] = Field(description="任务列表")


class ReplyGenerationResponse(BaseModel):
    """评论回复响应"""

    message: str = Field(description="生成的回复文案")
    rationale: str = Field(description="回复策略说明")
    follow_up_prompt: Optional[str] = Field(
        None, description="建议引导用户进一步互动的问题或行动"
    )


class KeywordSummaryRequest(BaseGenerationRequest):
    """关键词摘要请求"""

    goal_prompt: str = Field(description="活动目标，例如拉新、转化等")
    existing_keywords: Optional[Sequence[str]] = Field(default_factory=list, description="已存在的关键词列表")
    expecting_count: int = Field(1, le=20, description="希望提炼的关键词数量上限")


class KeywordSummaryResponse(BaseModel):
    """关键词摘要响应"""

    keywords: list[str] = Field(default_factory=list, description="提炼的关键词")
    count: int = Field(description="关键词数量")
    summary: str = Field(description="整体舆情摘要")

