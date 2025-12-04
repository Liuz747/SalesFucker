"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

from uuid import UUID
from typing import Optional, Any, Literal, Union, List

from pydantic import BaseModel, Field

from libs.types import InputContentParams, OutputContentParams
from .responses import BaseResponse


# 1. 定义具体的业务模型
class AppointmentOutput(BaseModel):
    type: Literal["appointment"]
    status: int
    time: int
    phone: str
    name: str
    project: str
    metadata: Optional[dict] = None


class SalesOutput(BaseModel):
    type: Literal["sales_summary"]
    order_id: str
    amount: float


class ThreadMetadata(BaseModel):
    """线程元数据模型"""
    
    tenant_id: Optional[str] = Field(None, description="租户标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")


class WorkflowData(BaseModel):
    """工作流数据模型"""
    
    type: str = Field(description="工作流数据类型")
    content: Any = Field(description="工作流数据内容")


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
    input: InputContentParams = Field(description="纯文本输入或多模态内容列表")


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
    status: str = Field(description="运行状态 (completed/failed)")
    response: str = Field(description="最终文本回复")
    
    # 指标封装
    metrics: Optional[dict] = Field(None, description="运行指标：tokens, time等")
    
    # 语音识别结果
    asr_results: Optional[list[dict]] = Field(None, description="用户语音输入的ASR结果")

    # 关键点：使用 Union + Discriminator 实现 business_outputs 的多态
    # 这样前端收到 type="appointment" 时，后端校验会自动匹配 AppointmentOutput 结构
    business_outputs: Optional[Union[AppointmentOutput, SalesOutput, dict]] = Field(
        None, 
        description="特定业务场景的结构化输出"
    )

    # 多模态统一列表
    multimodal_outputs: Optional[OutputContentParams] = Field(None, description="标准化的多模态输出流")
    
    
    metadata: Optional[dict] = Field(None, description="元数据")
