"""
通用响应基类

该模块定义了API响应的基础类，供各个领域的响应模型继承使用。

核心类:
- BaseResponse: 基础响应类，包含所有响应的标准字段
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from utils import get_current_timestamp_ms


class BaseResponse(BaseModel):
    """
    基础响应模型

    所有API响应的基础类，提供标准字段。
    域特定的响应模型应该继承此类。
    """

    model_config = {"exclude_none": True}

    code: int = Field(default=0, description="业务状态码，0表示成功")
    message: str = Field(default="success", description="响应消息")
    timestamp: int = Field(default_factory=get_current_timestamp_ms, description="响应时间戳")
    metadata: Optional[dict[str, Any]] = Field(None, description="响应元数据")
