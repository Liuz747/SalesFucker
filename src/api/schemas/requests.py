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

from pydantic import BaseModel, Field, field_validator


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

    class Config:
        """Pydantic配置"""

        json_encoders = {datetime: lambda v: v.isoformat()}


class PaginationRequest(BaseModel):
    """
    分页请求模型

    用于需要分页的API端点。
    """

    page: int = Field(1, ge=1, description="页码，从1开始")

    page_size: int = Field(20, ge=1, le=100, description="每页大小，最大100")

    sort_by: Optional[str] = Field(None, description="排序字段")

    sort_order: Optional[str] = Field(
        "desc", regex="^(asc|desc)$", description="排序方向：asc或desc"
    )

    @field_validator("page_size")
    def validate_page_size(cls, v):
        """验证页面大小"""
        if v > 100:
            raise ValueError("页面大小不能超过100")
        return v


class MessageRequest(BaseRequest):
    """
    消息请求模型

    用于发送单个消息的端点。
    """

    recipient: str = Field(description="接收方ID（智能体ID或用户ID）")

    message_type: str = Field(
        description="消息类型",
        regex="^(query|response|notification|trigger|suggestion)$",
    )

    content: str = Field(description="消息内容", min_length=1)

    attachments: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="消息附件"
    )

    priority: str = Field(
        "medium", regex="^(low|medium|high|urgent)$", description="消息优先级"
    )


class BulkOperationRequest(BaseRequest):
    """
    批量操作请求模型

    用于需要批量处理的端点。
    """

    operation: str = Field(description="操作类型")

    items: List[Dict[str, Any]] = Field(
        description="要处理的项目列表", min_items=1, max_items=100
    )

    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="操作选项"
    )

    @field_validator("items")
    def validate_items(cls, v):
        """验证项目列表"""
        if len(v) > 100:
            raise ValueError("批量操作项目数不能超过100")
        return v


class SearchRequest(PaginationRequest, BaseRequest):
    """
    搜索请求模型

    用于搜索相关的端点。
    """

    query: str = Field(description="搜索查询", min_length=1, max_length=200)

    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="搜索过滤条件"
    )

    search_type: str = Field(
        "semantic",
        regex="^(keyword|semantic|hybrid)$",
        description="搜索类型：keyword, semantic, hybrid",
    )

    include_fields: Optional[List[str]] = Field(None, description="要包含的字段列表")

    exclude_fields: Optional[List[str]] = Field(None, description="要排除的字段列表")
