"""
API数据模型模块

该模块定义了所有API端点的请求和响应数据模型。
使用Pydantic进行数据验证和序列化。

模型组织:
- requests.py: 通用请求模型
- responses.py: 通用响应模型
- agents.py: 智能体相关模型
- multimodal.py: 多模态处理模型
"""

# 专用模型
from .agents import (
    AgentCreateRequest,
    AgentListResponse,
    AgentStatusResponse,
    AgentTestRequest,
)
from .multimodal import (
    ImageAnalysisRequest,
    MultimodalRequest,
    MultimodalResponse,
    ProcessingStatusResponse,
    VoiceProcessingRequest,
)

# 通用模型
from .requests import BaseRequest, MessageRequest, PaginationRequest
from .responses import (
    ErrorResponse,
    PaginatedResponse,
    StatusResponse,
    SimpleResponse
)

__all__ = [
    # 通用请求模型
    "BaseRequest",
    "PaginationRequest",
    "MessageRequest",
    # 通用响应模型
    "ErrorResponse",
    "PaginatedResponse",
    "StatusResponse",
    "SimpleResponse",
    # 智能体模型
    "AgentCreateRequest",
    "AgentTestRequest",
    "AgentStatusResponse",
    "AgentListResponse",
    # 多模态模型
    "MultimodalRequest",
    "VoiceProcessingRequest",
    "ImageAnalysisRequest",
    "MultimodalResponse",
    "ProcessingStatusResponse",
]
