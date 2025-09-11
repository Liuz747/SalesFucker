"""
通用响应数据模型

该模块定义了API的通用响应数据模型，提供标准化的响应格式。

核心模型:
- BaseResponse: 基础响应模型
- ErrorResponse: 错误响应模型
- SuccessResponse: 成功响应模型
- PaginatedResponse: 分页响应模型
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# class BaseResponse(BaseModel):
#     """
#     基础响应模型
#
#     所有API响应的基础类。
#     """
#
#     success: Optional[bool] = Field(None, description="请求是否成功")
#
#     message: Optional[str] = Field(None, description="响应消息")
#
#     timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
#
#     request_id: Optional[str] = Field(None, description="关联的请求ID")
#
#     processing_time_ms: Optional[float] = Field(None, description="处理时间（毫秒）")
#
#     model_config = ConfigDict(
#         json_encoders={datetime: lambda v: v.isoformat()}
#     )


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


class ErrorResponse(BaseModel):
    """
    错误响应模型

    用于错误的API响应。
    """

    success: bool = Field(default=False)

    error: Dict[str, Any] = Field(description="错误信息")

    def __init__(self, **data):
        # 确保error字段有标准结构
        if "error" in data and isinstance(data["error"], dict):
            error_data = data["error"]
            if "code" not in error_data:
                error_data["code"] = "UNKNOWN_ERROR"
            if "message" not in error_data:
                error_data["message"] = "未知错误"
            if "details" not in error_data:
                error_data["details"] = None

        super().__init__(**data)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型

    用于分页数据的响应。
    """

    pagination: Optional[Dict[str, Any]] = Field(default={}, description="分页信息")

    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="请求成功", description="业务状态信息")
    data: List[T] = Field(default="请求数据", description="请求返回的数据")

    # todo 不确定要如何使用分页信息，先这样调整了。
    total: int = Field(description="分页信息")
    page: int = Field(description="分页信息")
    page_size: int = Field(description="分页信息")
    pages: int = Field(description="分页信息")

    def __init__(self, **data):
        # 确保pagination字段有标准结构
        if "pagination" in data and isinstance(data["pagination"], dict):
            pagination_data = data["pagination"]
            required_fields = ["page", "page_size", "total_items", "total_pages"]
            for field in required_fields:
                if field not in pagination_data:
                    pagination_data[field] = 0

        super().__init__(**data)
    @property
    def count(self) -> int:
        return len(self.data)  # 对实际数据而非类型操作
