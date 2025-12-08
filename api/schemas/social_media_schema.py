"""
社交媒体公域导流数据模型

定义请求与响应Schema，供FastAPI控制器及服务层复用。
"""

from collections.abc import Sequence
from typing import Optional

from pydantic import BaseModel, Field

from libs.types import SocialMediaActionType, SocialPlatform, MethodType, TextBeautifyActionType


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

    task: CommentData = Field(description="任务列表")


class CommentGenerationResponse(BaseModel):
    """评论生成响应"""

    actions: list[SocialMediaActionType] = Field(description="任务类型ID列表。必须返回列表，如果没有动作则返回空列表 []")
    message: str | None = Field(description="生成的评论文案。如果无法生成有效评论，返回 null")


class ReplyGenerationRequest(BaseGenerationRequest):
    """评论回复请求"""

    task_list: Sequence[ReplyData] = Field(description="任务列表")


class ReplyGenerationResponse(BaseModel):
    """评论回复响应"""

    tasks: Sequence[ReplyMessageData] = Field(default_factory=list, description="任务列表")


class KeywordSummaryRequest(BaseModel):
    """关键词生成请求"""

    product_prompt: str = Field(description="您的产品或服务。如医美、口腔、车贷等")
    existing_keywords: Optional[Sequence[str]] = Field(default_factory=list, description="已存在的关键词列表，生成时需要去重")
    expecting_count: int = Field(1, le=20, description="期望生成的关键词总数（包含existing_keywords）")


class KeywordSummaryResponse(BaseModel):
    """关键词摘要响应"""

    keywords: list[str] = Field(default_factory=list, description="提炼的关键词")
    count: int = Field(description="关键词数量")
    summary: str = Field(description="整体舆情摘要")


class ChatGenerationRequest(BaseGenerationRequest):
    """私聊回复请求"""

    content: str = Field(description="用户发送的消息内容")
    chat_prompt: Optional[str] = Field(None, description="私聊回复要求提示词或固定内容")


class ChatGenerationResponse(BaseModel):
    """私聊回复响应"""

    message: str = Field(description="生成的私聊回复内容")


class ReloadPromptRequest(BaseModel):
    """重载提示词请求"""

    method: MethodType = Field(description="提示词类型：comment/replies/keywords/private_message")


class ReloadPromptResponse(BaseModel):
    """重载提示词响应"""

    method: MethodType = Field(description="重载的提示词类型")
    message: str = Field(description="操作结果消息")


class MomentData(BaseModel):
    """朋友圈内容模型"""

    id: str = Field(description="朋友圈ID")
    thread_id: Optional[str] = Field(None, description="关联的Thread ID，用于记忆存储")
    moment_content: Optional[str] = Field(None, description="朋友圈文案内容")
    url_list: Optional[Sequence[str]] = Field(default_factory=list, description="朋友圈图片URL列表")


class MomentsAnalysisRequest(BaseModel):
    """朋友圈分析请求"""

    task_list: Sequence[MomentData] = Field(description="朋友圈内容列表")


class MomentsActionResult(BaseModel):
    """朋友圈互动结果"""

    id: str = Field(description="朋友圈ID")
    actions: Sequence[SocialMediaActionType] = Field(default_factory=list, description="互动类型列表：1=点赞，2=评论")
    message: Optional[str] = Field(None, description="评论内容，仅当actions包含2时有值")


class MomentsAnalysisResponse(BaseModel):
    """朋友圈分析响应"""

    tasks: Sequence[MomentsActionResult] = Field(default_factory=list, description="朋友圈互动结果列表")


class TextBeautifyRequest(BaseModel):
    """文本美化请求"""

    action_type: TextBeautifyActionType = Field(description="美化类型：1为缩写，2为扩写")
    source_text: str = Field(min_length=1, max_length=5000, description="待美化的原始文本")
    result_count: int = Field(default=3, ge=1, le=10, description="希望获得的文本数量")
    style: Optional[str] = Field(None, max_length=200, description="期望的风格描述")


class TextBeautifyResponse(BaseModel):
    """文本美化响应"""

    run_id: str = Field(description="运行标识符")
    status: str = Field(description="运行状态")
    response: Sequence[str] = Field(description="美化后的文本数组")
    input_tokens: int = Field(default=0, description="输入Token数")
    output_tokens: int = Field(default=0, description="输出Token数")
    processing_time: float = Field(description="处理时间（毫秒）")
    action_type: TextBeautifyActionType = Field(description="执行的美化类型")
