"""
社交媒体公域导流数据模型

定义请求与响应Schema，供FastAPI控制器及服务层复用。
"""

from collections.abc import Sequence
from typing import Optional

from pydantic import BaseModel, Field

from libs.types import SocialMediaActionType, SocialPlatform


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
    file_url: Optional[str] = Field(None, description="文件URL")
    reply_content: str = Field(description="回复内容")


class ReplyMessageData(BaseModel):
    """回复数据模型"""

    id: str = Field(description="回复ID")
    actions: Sequence[SocialMediaActionType] = Field(default_factory=list, description="任务类型ID")
    message: Optional[str] = Field(None, description="生成的评论文案")


class BaseGenerationRequest(BaseModel):
    """通用生成请求基础字段"""

    platform: SocialPlatform = Field(description="社交媒体平台")
    product_prompt: str = Field(description="您的产品或服务。如医美、口腔、车贷等")
    comment_type: Optional[int] = Field(None, description="AI评论为0，固定值评论为1")
    comment_prompt: Optional[str] = Field(None, description="评论风格")


class CommentGenerationRequest(BaseGenerationRequest):
    """评论生成请求"""

    task_list: Sequence[CommentData] = Field(description="任务列表")


class CommentGenerationResponse(BaseModel):
    """评论生成响应"""

    actions: Sequence[SocialMediaActionType] = Field(default_factory=list, description="任务类型ID")
    message: Optional[str] = Field(None, description="生成的评论文案")


class ReplyGenerationRequest(BaseGenerationRequest):
    """评论回复请求"""

    task_list: Sequence[ReplyData] = Field(description="任务列表")


class ReplyGenerationResponse(BaseModel):
    """评论回复响应"""

    tasks: Sequence[ReplyMessageData] = Field(default_factory=list, description="任务列表")


class KeywordSummaryRequest(BaseModel):
    """关键词生成请求"""

    platform: SocialPlatform = Field(description="社交媒体平台")
    product_prompt: str = Field(description="您的产品或服务。如医美、口腔、车贷等")
    existing_keywords: Optional[Sequence[str]] = Field(default_factory=list, description="已存在的关键词列表，生成时需要去重")
    expecting_count: int = Field(1, le=20, description="期望生成的关键词总数（包含existing_keywords）")


class KeywordSummaryResponse(BaseModel):
    """关键词摘要响应"""

    keywords: list[str] = Field(default_factory=list, description="提炼的关键词")
    count: int = Field(description="关键词数量")
    summary: str = Field(description="整体舆情摘要")

