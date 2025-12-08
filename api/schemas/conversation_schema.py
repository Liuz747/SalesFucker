"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from libs.types import MessageParams, OutputContentParams
from .responses import BaseResponse


@dataclass
class AppointmentOutput:
    status: int
    time: int
    service: str
    name: str
    phone: int


class ThreadMetadata(BaseModel):
    """线程元数据模型"""
    
    tenant_id: Optional[str] = Field(None, description="租户标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")


class WorkflowData(BaseModel):
    """工作流数据模型"""
    
    type: str = Field(description="工作流数据类型")
    content: str = Field(description="工作流数据内容")


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型"""
    
    thread_id: Optional[UUID] = Field(None, description="线程标识符")


class ThreadCreateResponse(BaseResponse):
    """线程创建响应模型"""
    
    thread_id: UUID = Field(description="创建的线程信息")


class MessageCreateRequest(BaseModel):
    """消息创建请求模型"""

    tenant_id: str = Field(description="租户标识符")
    assistant_id: UUID = Field(description="助手标识符")
    input: MessageParams = Field(description="消息列表，每个消息包含role和content")

    @field_validator('input')
    @classmethod
    def validate_input(cls, v: MessageParams) -> MessageParams:
        """验证输入消息列表至少包含一个用户消息"""
        if not any(msg.role == "user" for msg in v):
            raise ValueError("消息序列必须至少包含一个role='user'的消息")
        return v


class CallbackPayload(BaseModel):
    """回调载荷模型"""
    
    run_id: UUID = Field(description="运行标识符")
    thread_id: UUID = Field(description="线程标识符")
    status: str = Field(description="运行状态 (completed/failed)")
    data: Optional[WorkflowData] = Field(None, description="工作流处理结果")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    processing_time: float = Field(description="处理时间（毫秒）")
    finished_at: str = Field(description="完成时间（ISO格式字符串）")
    metadata: dict = Field(description="元数据信息")


class ThreadRunResponse(BaseModel):
    """线程运行响应模型"""

    run_id: UUID = Field(description="运行标识符")
    thread_id: UUID = Field(description="线程标识符")
    status: str = Field(description="运行状态")
    response: str = Field(description="最终文本回复")
    input_tokens: int = Field(default=0, description="输入Token数")
    output_tokens: int = Field(default=0, description="输出Token数")
    processing_time: float = Field(description="处理时间（毫秒）")
    asr_results: Optional[list[dict]] = Field(None, description="用户语音输入的ASR结果")
    multimodal_outputs: Optional[OutputContentParams] = Field(None, description="标准化的多模态输出流")
    invitation: Optional[AppointmentOutput] = Field(None, description="特定业务场景的结构化输出")
