from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from libs.types import EventType
from .responses import BaseResponse


class BasePayload(BaseModel):
    tenant_id: str = Field(description="租户标识符")
    assistant_id: UUID = Field(description="助手标识符")


class AppointmentEngagement(BasePayload):
    event_type: EventType = Field(description="事件类型")
    services: Optional[list[str]] = Field(None, description="服务列表")


class EngagementResponse(BaseResponse):
    response: str = Field(description="响应消息")
    input_tokens: int = Field(description="输入Token数")
    output_tokens: int = Field(description="输出Token数")
