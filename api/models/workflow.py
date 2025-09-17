from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Uuid, func

from utils import get_current_datetime
from .base import Base


class WorkflowOrm(Base):
    """工作流数据库ORM模型"""

    __tablename__ = "workflows"

    id = Column(Uuid, primary_key=True, autoincrement=True)
    workflow_id = Column(Uuid, nullable=False, index=True)
    thread_id = Column(Uuid, nullable=False, index=True)
    assistant_id = Column(Uuid, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkflowRun(BaseModel):
    """工作流模型"""

    run_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    input: str = Field(description="工作流内容")
    type: str = Field(description="工作流类型")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    finished_at: datetime = Field(default_factory=get_current_datetime, description="完成时间")


class WorkflowExecutionModel(BaseModel):
    """工作流执行模型"""

    execution_id: UUID = Field(description="执行标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    input_content: str = Field(description="输入内容")
    input_type: str = Field(default="text", description="输入类型")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    
    # 会话结果字段
    final_response: str = Field(default="", description="最终响应内容")
    processing_complete: bool = Field(default=False, description="是否处理完成")
    agent_responses: dict[str, Any] = Field(default_factory=dict, description="各智能体响应结果")