from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt, model_validator

from libs.types import Sex
from .responses import BaseResponse


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
    enable_trigger: Optional[bool] = Field(None, description="是否允许主动触发")
    enable_takeover: Optional[bool] = Field(None, description="是否允许AI接管")


class ThreadCreateResponse(BaseResponse):
    """线程创建响应模型"""

    thread_id: UUID = Field(description="创建的线程信息")


class ThreadBatchUpdatePayload(BaseModel):
    """批量更新线程"""

    is_converted: Optional[bool] = Field(None, description="客户是否已转化（已消费）")
    enable_trigger: Optional[bool] = Field(None, description="是否允许主动触发")
    enable_takeover: Optional[bool] = Field(None, description="是否允许AI接管")

    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        """确保至少提供一个更新字段"""
        if not any([
            self.is_converted is not None,
            self.enable_trigger is not None,
            self.enable_takeover is not None
        ]):
            raise ValueError("至少需要提供一个更新字段")
        return self


class ThreadBatchUpdateRequest(BaseModel):
    """批量更新请求模型"""

    thread_ids: list[UUID] = Field(description="线程ID列表", min_length=1, max_length=100)
    set_updates: ThreadBatchUpdatePayload = Field(description="要更新的字段")


class ThreadBatchUpdateResponse(BaseResponse):
    """批量更新响应模型（包含汇总统计）"""

    succeeded: int = Field(description="成功更新的线程数量")
    failed: int = Field(description="失败的线程数量")
    failed_ids: list[UUID] = Field(description="失败的线程ID结果列表")
