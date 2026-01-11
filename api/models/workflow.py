from collections.abc import Mapping
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Column, DateTime, String, Uuid, func

from libs.types import MessageParams
from utils import get_current_datetime
from .base import Base


class WorkflowOrm(Base):
    """工作流数据库ORM模型"""

    __tablename__ = "workflows"

    workflow_id = Column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    thread_id = Column(Uuid, nullable=False, index=True)
    assistant_id = Column(Uuid, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkflowRun(BaseModel):
    """工作流模型"""

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    type: Literal['chat', 'trigger'] = Field(description="工作流类型")
    inputs: MessageParams | None = Field(None, description="用户输入：消息列表")
    trigger_metadata: Mapping | None = Field(None, description="工作流元数据")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    finished_at: datetime = Field(default_factory=get_current_datetime, description="完成时间")

    @model_validator(mode='after')
    def validate_workflow_inputs(self):
        """
        验证工作流输入的完整性

        业务规则：
        - chat类型工作流必须提供input字段（用户消息）
        - trigger类型工作流必须提供trigger_metadata字段（触发事件元数据）
        """
        match self.type:
            case "chat":
                if not self.input:
                    raise ValueError("Chat workflow requires 'input' field with user messages")
            case "trigger":
                if not self.trigger_metadata:
                    raise ValueError("Trigger workflow requires 'trigger_metadata' field with event information")
        return self
