"""
通用响应数据模型

该模块定义了API的通用响应数据模型，提供标准化的响应格式。

核心模型:
- BaseResponse: 基础响应模型
- ErrorResponse: 错误响应模型
- SuccessResponse: 成功响应模型
- PaginatedResponse: 分页响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    """
    基础响应模型
    
    所有API响应的基础类。
    """
    
    success: bool = Field(
        description="请求是否成功"
    )
    
    message: Optional[str] = Field(
        None,
        description="响应消息"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳"
    )
    
    request_id: Optional[str] = Field(
        None,
        description="关联的请求ID"
    )
    
    processing_time_ms: Optional[float] = Field(
        None,
        description="处理时间（毫秒）"
    )
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SuccessResponse(BaseResponse, Generic[T]):
    """
    成功响应模型
    
    用于成功的API响应。
    """
    
    success: bool = Field(default=True)
    data: T = Field(description="响应数据")
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="响应元数据"
    )


class ErrorResponse(BaseResponse):
    """
    错误响应模型
    
    用于错误的API响应。
    """
    
    success: bool = Field(default=False)
    
    error: Dict[str, Any] = Field(
        description="错误信息"
    )
    
    def __init__(self, **data):
        # 确保error字段有标准结构
        if 'error' in data and isinstance(data['error'], dict):
            error_data = data['error']
            if 'code' not in error_data:
                error_data['code'] = 'UNKNOWN_ERROR'
            if 'message' not in error_data:
                error_data['message'] = '未知错误'
            if 'details' not in error_data:
                error_data['details'] = None
        
        super().__init__(**data)


class PaginatedResponse(SuccessResponse[List[T]]):
    """
    分页响应模型
    
    用于分页数据的响应。
    """
    
    pagination: Dict[str, Any] = Field(
        description="分页信息"
    )
    
    def __init__(self, **data):
        # 确保pagination字段有标准结构
        if 'pagination' in data and isinstance(data['pagination'], dict):
            pagination_data = data['pagination']
            required_fields = ['page', 'page_size', 'total_items', 'total_pages']
            for field in required_fields:
                if field not in pagination_data:
                    pagination_data[field] = 0
        
        super().__init__(**data)


class ConversationResponse(SuccessResponse[Dict[str, Any]]):
    """
    对话响应模型
    
    用于对话处理的响应。
    """
    
    conversation_id: str = Field(
        description="对话ID"
    )
    
    agent_responses: Dict[str, Any] = Field(
        description="智能体响应信息"
    )
    
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="更新的对话上下文"
    )
    
    suggestions: Optional[List[str]] = Field(
        None,
        description="建议的后续问题"
    )


class StatusResponse(SuccessResponse[Dict[str, Any]]):
    """
    状态响应模型
    
    用于系统状态和健康检查的响应。
    """
    
    component: str = Field(
        description="组件名称"
    )
    
    status: str = Field(
        description="状态",
        regex="^(healthy|warning|critical|maintenance)$"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="详细状态信息"
    )
    
    metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="性能指标"
    )


class BatchOperationResponse(SuccessResponse[Dict[str, Any]]):
    """
    批量操作响应模型
    
    用于批量操作的响应。
    """
    
    total_items: int = Field(
        description="总项目数"
    )
    
    successful_items: int = Field(
        description="成功处理的项目数"
    )
    
    failed_items: int = Field(
        description="失败的项目数"
    )
    
    results: List[Dict[str, Any]] = Field(
        description="详细结果列表"
    )
    
    errors: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="错误信息列表"
    )


class SearchResponse(PaginatedResponse[Dict[str, Any]]):
    """
    搜索响应模型
    
    用于搜索结果的响应。
    """
    
    query: str = Field(
        description="搜索查询"
    )
    
    search_type: str = Field(
        description="搜索类型"
    )
    
    facets: Optional[Dict[str, Any]] = Field(
        None,
        description="搜索聚合结果"
    )
    
    suggestions: Optional[List[str]] = Field(
        None,
        description="搜索建议"
    )


class HealthCheckResponse(StatusResponse):
    """
    健康检查响应模型
    
    专门用于健康检查端点。
    """
    
    version: str = Field(
        description="系统版本"
    )
    
    uptime: str = Field(
        description="运行时间"
    )
    
    dependencies: Optional[Dict[str, str]] = Field(
        None,
        description="依赖服务状态"
    )


class AsyncTaskResponse(SuccessResponse[Dict[str, Any]]):
    """
    异步任务响应模型
    
    用于异步处理任务的响应。
    """
    
    task_id: str = Field(
        description="任务ID"
    )
    
    task_status: str = Field(
        description="任务状态",
        regex="^(pending|running|completed|failed|cancelled)$"
    )
    
    progress: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="任务进度百分比"
    )
    
    estimated_completion: Optional[datetime] = Field(
        None,
        description="预计完成时间"
    )
    
    result_url: Optional[str] = Field(
        None,
        description="结果获取URL"
    )