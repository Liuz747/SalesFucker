from collections.abc import Sequence
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Uuid, func

from utils import get_current_datetime
from schemas.conversation_schema import InputContent
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
    input: str | Sequence[InputContent] = Field(description="用户输入：纯文本或多模态内容序列")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    finished_at: datetime = Field(default_factory=get_current_datetime, description="完成时间")
