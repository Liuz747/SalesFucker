"""
通用请求数据模型

该模块定义了API的通用请求数据模型，提供基础的请求结构和验证。

核心模型:
- BaseRequest: 基础请求模型
- PaginationRequest: 分页请求模型
- MessageRequest: 消息请求模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class BaseRequest(BaseModel):
    """
    基础请求模型

    所有API请求的基础类，提供通用字段和验证。
    """

    request_id: Optional[str] = Field(
        None, description="请求唯一标识符，用于追踪和调试"
    )

    timestamp: Optional[datetime] = Field(None, description="请求时间戳")

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="请求元数据"
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class PaginationRequest(BaseModel):
    """
    分页请求模型

    用于需要分页的API端点。
    """

    page: int = Field(1, ge=1, description="页码，从1开始")

    page_size: int = Field(20, ge=1, le=100, description="每页大小，最大100")

    sort_by: Optional[str] = Field(None, description="排序字段")

    sort_order: Optional[str] = Field(
        "desc", pattern="^(asc|desc)$", description="排序方向：asc或desc"
    )

    @field_validator("page_size")
    def validate_page_size(cls, v):
        """验证页面大小"""
        if v > 100:
            raise ValueError("页面大小不能超过100")
        return v
