from datetime import datetime
from uuid import UUID
from typing import Any, Optional
from collections.abc import Mapping

from pydantic import BaseModel, Field, ConfigDict
from utils import get_current_datetime


class WorkflowExecutionModel(BaseModel):
    """工作流执行模型"""

    # 允许动态添加字段（用于workflow节点间传递数据）
    model_config = ConfigDict(extra='allow')

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")

    next_node: Optional[str] = Field(default=None, description="下一个节点")
    input: str = Field(description="输入内容")
    output: Optional[str] = Field(default=None, description="输入类型")
    values: Optional[Mapping[str, Any]] = Field(default=None, description="工作流节点交互的状态")

    total_tokens: Optional[int] = Field(default=None, description="总Token数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    exception_count: int = Field(default=0, description="异常次数")

    started_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    finished_at: Optional[datetime] = Field(default=None, description="创建时间")
