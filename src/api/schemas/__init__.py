"""
API数据模型模块

该模块定义了所有API端点的请求和响应数据模型。
使用Pydantic进行数据验证和序列化。

模型组织:
- requests.py: 通用请求模型
- responses.py: 通用响应模型
- agents.py: 智能体相关模型
- llm.py: LLM管理相关模型
- multimodal.py: 多模态处理模型
"""

# 通用模型
from .requests import (
    BaseRequest,
    PaginationRequest,
    ConversationRequest,
    MessageRequest
)

from .responses import (
    BaseResponse,
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse,
    ConversationResponse,
    StatusResponse
)

# 专用模型
from .agents import (
    AgentCreateRequest,
    AgentTestRequest,
    AgentStatusResponse,
    AgentListResponse
)

from .llm import (
    LLMConfigRequest,
    ProviderStatusRequest,
    OptimizationRequest,
    LLMStatusResponse,
    CostAnalysisResponse
)

from .multimodal import (
    MultimodalRequest,
    VoiceProcessingRequest,
    ImageAnalysisRequest,
    MultimodalResponse,
    ProcessingStatusResponse
)

__all__ = [
    # 通用请求模型
    "BaseRequest",
    "PaginationRequest", 
    "ConversationRequest",
    "MessageRequest",
    
    # 通用响应模型
    "BaseResponse",
    "ErrorResponse",
    "SuccessResponse",
    "PaginatedResponse",
    "ConversationResponse", 
    "StatusResponse",
    
    # 智能体模型
    "AgentCreateRequest",
    "AgentTestRequest",
    "AgentStatusResponse",
    "AgentListResponse",
    
    # LLM管理模型
    "LLMConfigRequest",
    "ProviderStatusRequest", 
    "OptimizationRequest",
    "LLMStatusResponse",
    "CostAnalysisResponse",
    
    # 多模态模型
    "MultimodalRequest",
    "VoiceProcessingRequest",
    "ImageAnalysisRequest", 
    "MultimodalResponse",
    "ProcessingStatusResponse"
]