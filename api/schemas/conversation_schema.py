"""
对话工作区架构模块

该模块从业务模型导入必要的架构定义，提供纯数据结构的Thread模型。
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from libs.types import MessageParams, OutputContentParams, Sex
from .responses import BaseResponse


@dataclass
class AppointmentOutput:
    status: int
    time: Optional[int] = None
    service: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[int] = None


class ThreadMetadata(BaseModel):
    """线程元数据模型"""

    tenant_id: Optional[str] = Field(None, description="租户标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")


class WorkflowData(BaseModel):
    """工作流数据模型"""

    type: str = Field(description="工作流数据类型")
    content: str = Field(description="工作流数据内容")


class ThreadCreateRequest(BaseModel):
    """线程创建请求模型 - 要求必填字段以识别客户"""

    name: str = Field(..., description="客户姓名（必填）")
    phone: str = Field(..., description="客户电话（必填）")
    sex: Optional[Sex] = Field(None, description="客户性别")
    age: Optional[int] = Field(None, description="客户年龄")
    occupation: Optional[str] = Field(None, description="客户职业")
    services: Optional[list[str]] = Field(default_factory=list, description="客户已消费的服务列表")
    is_converted: bool = Field(default=False, description="客户是否已转化（已消费）")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        if not v:
            raise ValueError('手机号不能为空')

        # 去除空格和其他非数字字符
        cleaned_phone = re.sub(r'[^\d]', '', v)

        # 验证中国大陆手机号格式（1开头的11位数字）
        if not re.match(r'^1[3-9]\d{9}$', cleaned_phone):
            raise ValueError('手机号格式不正确，请输入有效的中国大陆手机号')

        return cleaned_phone

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证客户姓名"""
        if not v or not v.strip():
            raise ValueError('客户姓名不能为空')

        # 去除前后空格
        cleaned_name = v.strip()

        # 基本长度检查
        if len(cleaned_name) < 1:
            raise ValueError('客户姓名长度至少为1个字符')
        if len(cleaned_name) > 50:
            raise ValueError('客户姓名长度不能超过50个字符')

        return cleaned_name

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """验证年龄范围"""
        if v is not None:
            if v < 0 or v > 150:
                raise ValueError('年龄必须在0-150之间')
        return v


class ThreadUpdateRequest(BaseModel):
    """线程更新请求模型 - 支持部分更新客户信息"""

    name: Optional[str] = Field(None, description="客户姓名")
    phone: Optional[str] = Field(None, description="客户电话")
    sex: Optional[Sex] = Field(None, description="客户性别")
    age: Optional[int] = Field(None, description="客户年龄")
    occupation: Optional[str] = Field(None, description="客户职业")
    services: Optional[list[str]] = Field(None, description="客户已消费的服务列表")
    is_converted: Optional[bool] = Field(None, description="客户是否已转化（已消费）")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """验证手机号格式（如果提供）"""
        if v is not None:
            if not v.strip():
                raise ValueError('手机号不能为空字符串')

            # 去除空格和其他非数字字符
            cleaned_phone = re.sub(r'[^\d]', '', v)

            # 验证中国大陆手机号格式
            if not re.match(r'^1[3-9]\d{9}$', cleaned_phone):
                raise ValueError('手机号格式不正确，请输入有效的中国大陆手机号')

            return cleaned_phone
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证客户姓名（如果提供）"""
        if v is not None:
            if not v.strip():
                raise ValueError('客户姓名不能为空字符串')

            cleaned_name = v.strip()

            # 基本长度检查
            if len(cleaned_name) < 1:
                raise ValueError('客户姓名长度至少为1个字符')
            if len(cleaned_name) > 50:
                raise ValueError('客户姓名长度不能超过50个字符')

            return cleaned_name
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """验证年龄范围"""
        if v is not None:
            if v < 0 or v > 150:
                raise ValueError('年龄必须在0-150之间')
        return v


class ThreadPayload(BaseModel):
    """线程创建/更新通用模型 - 已弃用，请使用ThreadCreateRequest或ThreadUpdateRequest"""

    name: Optional[str] = Field(None, description="客户姓名")
    sex: Optional[Sex] = Field(None, description="客户性别")
    age: Optional[int] = Field(None, description="客户年龄")
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
    response: str | Sequence[str] = Field(description="最终文本回复")
    input_tokens: int = Field(default=0, description="输入Token数")
    output_tokens: int = Field(default=0, description="输出Token数")
    processing_time: float = Field(description="处理时间（毫秒）")
    asr_results: Optional[list[dict]] = Field(None, description="用户语音输入的ASR结果")
    multimodal_outputs: Optional[OutputContentParams] = Field(None, description="标准化的多模态输出流")
    invitation: Optional[AppointmentOutput] = Field(None, description="特定业务场景的结构化输出")
