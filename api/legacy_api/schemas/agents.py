"""
智能体相关数据模型

该模块定义了智能体管理和操作相关的请求和响应数据模型。

核心模型:
- AgentCreateRequest: 智能体创建请求
- AgentTestRequest: 智能体测试请求
- AgentStatusResponse: 智能体状态响应
- AgentListResponse: 智能体列表响应
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .requests import BaseRequest
from .responses import PaginatedResponse, SuccessResponse


class AgentCreateRequest(BaseRequest):
    """
    智能体创建请求模型
    """

    agent_type: str = Field(
        description="智能体类型",
        pattern="^(compliance|sentiment|intent|sales|product|memory|strategy|proactive|suggestion)$",
    )

    tenant_id: str = Field(description="租户ID", min_length=3, max_length=50)

    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="智能体配置参数"
    )

    auto_activate: bool = Field(True, description="是否自动激活智能体")

    @field_validator("tenant_id")
    def validate_tenant_id(cls, v):
        """验证租户ID格式"""
        if not v.isalnum():
            raise ValueError("租户ID只能包含字母和数字")
        return v


class AgentTestRequest(BaseRequest):
    """
    智能体测试请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    
    agent_id: Optional[str] = Field(
        None, description="要测试的智能体ID，如果不提供则自动选择"
    )

    test_message: str = Field(description="测试消息内容", min_length=1, max_length=1000)

    test_type: str = Field(
        "functional",
        pattern="^(functional|performance|integration)$",
        description="测试类型",
    )

    expected_result: Optional[Dict[str, Any]] = Field(
        None, description="预期结果（用于验证）"
    )

    timeout_seconds: int = Field(30, ge=1, le=300, description="测试超时时间（秒）")


class AgentBatchTestRequest(BaseRequest):
    """
    智能体批量测试请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    
    agent_ids: List[str] = Field(
        description="要测试的智能体ID列表", min_items=1, max_items=20
    )

    test_cases: List[Dict[str, Any]] = Field(description="测试用例列表", min_items=1)

    parallel_execution: bool = Field(True, description="是否并行执行测试")


class AgentConfigUpdateRequest(BaseRequest):
    """
    智能体配置更新请求模型
    """

    config_updates: Dict[str, Any] = Field(description="要更新的配置项")

    merge_config: bool = Field(True, description="是否合并配置（False表示完全替换）")

    restart_agent: bool = Field(False, description="是否重启智能体以应用配置")


# 响应模型


class AgentInfo(BaseModel):
    """智能体信息模型"""

    agent_id: str = Field(description="智能体ID")
    agent_type: str = Field(description="智能体类型")
    tenant_id: str = Field(description="租户ID")
    is_active: bool = Field(description="是否激活")
    created_at: datetime = Field(description="创建时间")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")

    # 统计信息
    messages_processed: int = Field(0, description="已处理消息数")
    success_rate: float = Field(0.0, description="成功率")
    average_response_time: float = Field(0.0, description="平均响应时间（毫秒）")

    # 配置信息
    config: Dict[str, Any] = Field(default_factory=dict, description="当前配置")
    capabilities: List[str] = Field(default_factory=list, description="智能体能力列表")


class AgentStatusResponse(SuccessResponse[AgentInfo]):
    """
    智能体状态响应模型
    """

    health_status: str = Field(
        description="健康状态", pattern="^(healthy|warning|critical)$"
    )

    performance_metrics: Dict[str, Any] = Field(description="性能指标")

    recent_errors: Optional[List[Dict[str, Any]]] = Field(
        None, description="最近的错误信息"
    )


class AgentListResponse(PaginatedResponse[AgentInfo]):
    """
    智能体列表响应模型
    """

    summary: Dict[str, Any] = Field(description="汇总信息")

    filters_applied: Optional[Dict[str, Any]] = Field(
        None, description="应用的过滤条件"
    )


class AgentTestResult(BaseModel):
    """智能体测试结果模型"""

    agent_id: str = Field(description="智能体ID")
    test_type: str = Field(description="测试类型")
    success: bool = Field(description="测试是否成功")

    # 测试指标
    response_time_ms: float = Field(description="响应时间（毫秒）")
    memory_usage_mb: Optional[float] = Field(None, description="内存使用（MB）")

    # 测试结果
    actual_result: Dict[str, Any] = Field(description="实际结果")
    expected_result: Optional[Dict[str, Any]] = Field(None, description="预期结果")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误消息")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

    timestamp: datetime = Field(default_factory=datetime.now, description="测试时间")


class AgentTestResponse(SuccessResponse[AgentTestResult]):
    """
    智能体测试响应模型
    """

    test_id: str = Field(description="测试ID")
    recommendations: Optional[List[str]] = Field(None, description="优化建议")


class AgentBatchTestResponse(SuccessResponse[List[AgentTestResult]]):
    """
    智能体批量测试响应模型
    """

    summary: Dict[str, Any] = Field(description="测试汇总")

    failed_tests: List[str] = Field(description="失败的测试ID列表")


class AgentOperationResponse(SuccessResponse[Dict[str, Any]]):
    """
    智能体操作响应模型

    用于激活、停用、重启等操作的响应。
    """

    operation: str = Field(description="执行的操作")
    agent_id: str = Field(description="智能体ID")
    previous_state: Optional[Dict[str, Any]] = Field(None, description="操作前状态")
    current_state: Dict[str, Any] = Field(description="操作后状态")


class AgentMetricsResponse(SuccessResponse[Dict[str, Any]]):
    """
    智能体指标响应模型
    """

    agent_id: str = Field(description="智能体ID")
    time_range: Dict[str, datetime] = Field(description="指标时间范围")

    # 性能指标
    performance_metrics: Dict[str, float] = Field(description="性能指标")

    # 业务指标
    business_metrics: Dict[str, Any] = Field(description="业务指标")

    # 趋势数据
    trends: Optional[Dict[str, List[float]]] = Field(None, description="趋势数据")
