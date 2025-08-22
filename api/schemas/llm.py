"""
LLM管理相关数据模型

该模块定义了LLM提供商管理、优化和监控相关的请求和响应数据模型。

核心模型:
- LLMConfigRequest: LLM配置请求
- ProviderStatusRequest: 提供商状态请求
- OptimizationRequest: 优化请求
- LLMStatusResponse: LLM状态响应
- CostAnalysisResponse: 成本分析响应
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .requests import BaseRequest
from .responses import SuccessResponse


class LLMProviderType(StrEnum):
    """LLM提供商类型枚举"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class LLMConfigRequest(BaseRequest):
    """
    LLM配置请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)

    provider: LLMProviderType = Field(description="LLM提供商")

    model_name: str = Field(description="模型名称", min_length=1)

    api_key: Optional[str] = Field(
        None, description="API密钥（敏感信息，仅在需要时提供）"
    )

    endpoint_url: Optional[str] = Field(None, description="自定义API端点URL")

    model_params: Dict[str, Any] = Field(
        default_factory=dict, description="模型配置参数"
    )

    rate_limits: Optional[Dict[str, int]] = Field(None, description="速率限制配置")

    priority: int = Field(1, ge=1, le=10, description="提供商优先级（1-10）")

    enabled: bool = Field(True, description="是否启用")


class ProviderStatusRequest(BaseRequest):
    """
    提供商状态请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)

    provider: Optional[LLMProviderType] = Field(
        None, description="指定提供商，为空则查询所有"
    )

    include_metrics: bool = Field(True, description="是否包含性能指标")

    time_range_hours: int = Field(24, ge=1, le=168, description="指标时间范围（小时）")


# 响应模型
class ProviderInfo(BaseModel):
    """提供商信息模型"""

    provider: LLMProviderType = Field(description="提供商类型")
    model_name: str = Field(description="模型名称")
    status: str = Field(description="状态", pattern="^(active|inactive|error)$")
    enabled: bool = Field(description="是否启用")
    priority: int = Field(description="优先级")

    # 连接信息
    endpoint_url: Optional[str] = Field(None, description="API端点")
    last_health_check: Optional[datetime] = Field(None, description="最后健康检查时间")

    # 配置信息
    rate_limits: Dict[str, int] = Field(default_factory=dict, description="速率限制")
    model_params: Dict[str, Any] = Field(default_factory=dict, description="模型配置")



class LLMStatusResponse(SuccessResponse[Dict[str, Any]]):
    """
    LLM状态响应模型
    """

    global_status: str = Field(
        description="全局状态", pattern="^(healthy|warning|critical)$"
    )

    providers: List[ProviderInfo] = Field(description="提供商列表")

    routing_config: Dict[str, Any] = Field(description="当前路由配置")

    system_metrics: Optional[Dict[str, Any]] = Field(None, description="系统级指标")


class CostAnalysisResponse(SuccessResponse[Dict[str, Any]]):
    """
    成本分析响应模型
    """

    total_cost: float = Field(description="总成本（美元）")
    cost_breakdown: Dict[LLMProviderType, float] = Field(description="成本分解")

    # 预算信息
    monthly_budget: Optional[float] = Field(None, description="月度预算")
    budget_utilization: Optional[float] = Field(None, description="预算使用率")

    # 成本趋势
    daily_costs: List[Dict[str, Any]] = Field(description="日成本数据")
    cost_trends: Dict[str, List[float]] = Field(description="成本趋势")

    # 优化建议
    optimization_suggestions: List[Dict[str, Any]] = Field(description="成本优化建议")
