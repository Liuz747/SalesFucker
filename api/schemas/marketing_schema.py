from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MarketingPlanOption(BaseModel):
    """营销计划选项"""
    option_id: int = Field(description="选项ID (1-3)")
    content: str = Field(description="方案内容")


class MarketingPlanRequest(BaseModel):
    """营销计划生成请求"""
    request_id: Optional[UUID] = Field(default=None, description="会话线程ID，用于多轮对话上下文（可选，首次请求留空）")
    content: str = Field(description="营销方案描述")


class MarketingPlanResponse(BaseModel):
    """营销计划生成响应"""
    request_id: UUID = Field(description="请求ID")
    response: str = Field(description="营销方案分析和建议")
    options: list[MarketingPlanOption] = Field(description="3个结构化的营销方案选项")
    input_tokens: int = Field(description="输入token数")
    output_tokens: int = Field(description="输出token数")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
