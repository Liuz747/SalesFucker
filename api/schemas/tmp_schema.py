from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from typing import Dict, List, Optional, Any

T = TypeVar("T")


class SimpleResponse(BaseModel, Generic[T]):
    """
    成功响应模型

    用于成功的API响应。
    """

    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="请求成功", description="业务状态信息")
    request_id: Optional[str] = Field(None, description="关联的请求ID")
    handler_process_time: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    # success: Optional[bool] = Field(default=None)
    data: Optional[T] = Field(default=None, description="响应数据")

    metadata: Optional[Dict[str, Any]] = Field(None, description="响应元数据")
