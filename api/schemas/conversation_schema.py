"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

from collections.abc import Sequence
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, PositiveInt

from libs.types import MessageParams, OutputContentParams, Sex
from .responses import BaseResponse


class InvitationData(BaseModel):
    """邀约信息数据模型"""
    status: Literal[0, 1] = Field(default=0, description="邀约状态: 0=不邀约, 1=确认邀约")
    time: int = Field(default=0, description="预约时间戳（毫秒），status=1时必须有值")
    service: Optional[str] = Field(default=None, description="服务项目")
    name: Optional[str] = Field(default=None, description="客户姓名")
    phone: Optional[str] = Field(default=None, description="联系电话")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone_number(cls, v) -> Optional[str]:
        """验证手机号格式（中国11位手机号）"""
        if v is None:
            return None

        phone_str = str(v) if not isinstance(v, str) else v

        if len(phone_str) == 11 and phone_str.startswith('1'):
            return phone_str

        return None


class ThreadPayload(BaseModel):
    """线程更新模型"""

    name: Optional[str] = Field(None, description="客户姓名")
    nickname: Optional[str] = Field(None, description="客户昵称")
    real_name: Optional[str] = Field(None, description="客户真实姓名")
    sex: Optional[Sex] = Field(None, description="客户性别")
    age: Optional[PositiveInt] = Field(None, description="客户年龄")
    phone: Optional[str] = Field(None, description="客户电话")
    occupation: Optional[str] = Field(None, description="客户职业")
    services: Optional[list[str]] = Field(None, description="客户已消费的服务列表")
    is_converted: Optional[bool] = Field(None, description="客户是否已转化（已消费）")


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
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    status: str = Field(description="运行状态 (completed/failed)")
    data: Optional[dict] = Field(None, description="工作流处理结果")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    processing_time: float = Field(description="处理时间（毫秒）")
    finished_at: int = Field(description="完成时间戳")
    metadata: Optional[dict] = Field(None, description="元数据信息")


class ThreadRunResponse(BaseModel):
    """线程运行响应模型"""

    run_id: UUID = Field(description="运行标识符")
    thread_id: UUID = Field(description="线程标识符")
    status: str = Field(description="运行状态")
    response: str | Sequence[str] = Field(description="最终文本回复")
    input_tokens: int = Field(default=0, description="输入Token数")
    output_tokens: int = Field(default=0, description="输出Token数")
    processing_time: float = Field(description="处理时间（毫秒）")
    asr_results: Optional[list[dict]] = Field(None, description="用户语音输入的ASR结果")
    multimodal_outputs: Optional[OutputContentParams] = Field(None, description="标准化的多模态输出流")
    invitation: Optional[InvitationData] = Field(None, description="特定业务场景的结构化输出")
    assets_data: Optional[dict] = Field(None, description="素材数据（当检测到素材意向时返回）")
