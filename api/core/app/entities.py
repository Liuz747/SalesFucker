from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field
from utils import get_current_datetime


class WorkflowExecutionModel(BaseModel):
    """工作流执行模型"""

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    input: str = Field(description="输入内容")
    type: str = Field(default="text", description="输入类型")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    
    # 会话结果字段
    final_response: str = Field(default="", description="最终响应内容")
    processing_complete: bool = Field(default=False, description="是否处理完成")
    agent_responses: dict[str, Any] = Field(default_factory=dict, description="各智能体响应结果")