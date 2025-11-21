"""
工作流运行业务模型模块
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from libs.types import InputContentParams, OutputContentParams, OutputType
from utils import get_current_datetime


class WorkflowExecutionModel(BaseModel):
    """工作流执行模型"""

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")

    input: InputContentParams = Field(description="输入内容")
    output: Optional[str] = Field(default=None, description="文本输出内容")
    values: Optional[Mapping[str, Any]] = Field(default=None, description="工作流节点交互的状态")

    # 多模态输出 - 支持音频、图像、视频等
    multimodal_outputs: Optional[OutputContentParams] = Field(
        default=None,
        description="多模态输出列表（音频、图像、视频等）"
    )
    actions: Optional[list[OutputType]] = Field(
        default=None,
        description="输出类型列表，例如：['output_audio', 'output_image']"
    )

    total_tokens: Optional[int] = Field(default=None, description="总Token数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    exception_count: int = Field(default=0, description="异常次数")

    started_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    finished_at: Optional[datetime] = Field(default=None, description="创建时间")
