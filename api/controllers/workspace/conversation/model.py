"""
对话模型模块
"""
from datetime import datetime
from typing import Optional, List, Self

from pydantic import BaseModel, Field

from utils import get_current_datetime
from models import ThreadStatus, ThreadOrm
from .schema import ThreadMetadata, WorkflowData


class Thread(BaseModel):
    """对话线程数据模型"""
    
    thread_id: str = Field(description="线程标识符")
    assistant_id: Optional[str] = Field(None, description="助手标识符")
    status: ThreadStatus = Field(default=ThreadStatus.ACTIVE, description="线程状态")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")
    processing_time: Optional[float] = Field(None, description="处理时间（毫秒）")
    metadata: ThreadMetadata = Field(description="线程元数据")


class Workflow(BaseModel):
    """工作流模型"""
    
    id: str = Field(description="工作流标识符")
    thread_id: str = Field(description="线程标识符")
    data: List[WorkflowData] = Field(description="工作流数据")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")