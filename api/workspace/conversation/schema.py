"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""
from typing import Optional

from pydantic import BaseModel, Field

# 从业务模型导入
from models import ThreadMetadata


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型"""
    
    thread_id: Optional[str] = Field(None, description="线程标识符", min_length=1, max_length=100)
    assistant_id: str = Field(description="助手标识符", min_length=1, max_length=100)
    metadata: ThreadMetadata = Field(description="线程元数据，必须包含tenant_id")

