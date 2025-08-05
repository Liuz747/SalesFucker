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

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum

from .requests import BaseRequest
from .responses import SuccessResponse, PaginatedResponse


class LLMProviderType(str, Enum):
    """LLM提供商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class RoutingStrategy(str, Enum):
    """路由策略枚举"""
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    AGENT_OPTIMIZED = "agent_optimized"
    ROUND_ROBIN = "round_robin"


class LLMConfigRequest(BaseRequest):
    """
    LLM配置请求模型
    """
    
    provider: LLMProviderType = Field(
        description="LLM提供商"
    )
    
    model_name: str = Field(
        description="模型名称",
        min_length=1
    )
    
    api_key: Optional[str] = Field(
        None,
        description="API密钥（敏感信息，仅在需要时提供）"
    )
    
    endpoint_url: Optional[str] = Field(
        None,
        description="自定义API端点URL"
    )
    
    model_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="模型配置参数"
    )
    
    rate_limits: Optional[Dict[str, int]] = Field(
        None,
        description="速率限制配置"
    )
    
    priority: int = Field(
        1,
        ge=1,
        le=10,
        description="提供商优先级（1-10）"
    )
    
    enabled: bool = Field(
        True,
        description="是否启用"
    )


class ProviderStatusRequest(BaseRequest):
    """
    提供商状态请求模型
    """
    
    provider: Optional[LLMProviderType] = Field(
        None,
        description="指定提供商，为空则查询所有"
    )
    
    include_metrics: bool = Field(
        True,
        description="是否包含性能指标"
    )
    
    time_range_hours: int = Field(
        24,
        ge=1,
        le=168,
        description="指标时间范围（小时）"
    )


class OptimizationRequest(BaseRequest):
    """
    优化请求模型
    """
    
    optimization_type: str = Field(
        description="优化类型",
        regex="^(cost|performance|quality|latency)$"
    )
    
    target_agents: Optional[List[str]] = Field(
        None,
        description="目标智能体类型列表"
    )
    
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="优化约束条件"
    )
    
    dry_run: bool = Field(
        False,
        description="是否为试运行（不实际应用优化）"
    )


class RoutingConfigRequest(BaseRequest):
    """
    路由配置请求模型
    """
    
    strategy: RoutingStrategy = Field(
        description="路由策略"
    )
    
    agent_preferences: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description="智能体特定偏好"
    )
    
    fallback_provider: Optional[LLMProviderType] = Field(
        None,
        description="备用提供商"
    )
    
    health_check_interval: int = Field(
        60,
        ge=10,
        le=3600,
        description="健康检查间隔（秒）"
    )


class CostBudgetRequest(BaseRequest):
    """
    成本预算请求模型
    """
    
    monthly_budget: float = Field(
        ge=0,
        description="月度预算（美元）"
    )
    
    provider_allocations: Optional[Dict[LLMProviderType, float]] = Field(
        None,
        description="提供商预算分配比例"
    )
    
    alert_thresholds: Optional[Dict[str, float]] = Field(
        None,
        description="告警阈值配置"
    )


# 响应模型

class ProviderInfo(BaseModel):
    """提供商信息模型"""
    
    provider: LLMProviderType = Field(description="提供商类型")
    model_name: str = Field(description="模型名称")
    status: str = Field(description="状态", regex="^(active|inactive|error)$")
    enabled: bool = Field(description="是否启用")
    priority: int = Field(description="优先级")
    
    # 连接信息
    endpoint_url: Optional[str] = Field(None, description="API端点")
    last_health_check: Optional[datetime] = Field(None, description="最后健康检查时间")
    
    # 配置信息
    rate_limits: Dict[str, int] = Field(default_factory=dict, description="速率限制")
    model_config: Dict[str, Any] = Field(default_factory=dict, description="模型配置")


class ProviderMetrics(BaseModel):
    """提供商指标模型"""
    
    provider: LLMProviderType = Field(description="提供商")
    
    # 使用统计
    total_requests: int = Field(description="总请求数")
    successful_requests: int = Field(description="成功请求数")
    failed_requests: int = Field(description="失败请求数")
    
    # 性能指标
    average_latency_ms: float = Field(description="平均延迟（毫秒）")
    p95_latency_ms: float = Field(description="95分位延迟（毫秒）")
    p99_latency_ms: float = Field(description="99分位延迟（毫秒）")
    
    # 成本信息
    total_cost_usd: float = Field(description="总成本（美元）")
    cost_per_request: float = Field(description="每请求成本")
    token_usage: Dict[str, int] = Field(description="Token使用统计")
    
    # 时间范围
    time_range: Dict[str, datetime] = Field(description="统计时间范围")


class LLMStatusResponse(SuccessResponse[Dict[str, Any]]):
    """
    LLM状态响应模型
    """
    
    global_status: str = Field(
        description="全局状态",
        regex="^(healthy|warning|critical)$"
    )
    
    providers: List[ProviderInfo] = Field(
        description="提供商列表"
    )
    
    routing_config: Dict[str, Any] = Field(
        description="当前路由配置"
    )
    
    system_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="系统级指标"
    )


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
    optimization_suggestions: List[Dict[str, Any]] = Field(
        description="成本优化建议"
    )


class OptimizationResponse(SuccessResponse[Dict[str, Any]]):
    """
    优化响应模型
    """
    
    optimization_type: str = Field(description="优化类型")
    
    # 优化结果
    recommendations: List[Dict[str, Any]] = Field(description="优化建议")
    estimated_savings: Optional[Dict[str, float]] = Field(None, description="预估节省")
    
    # 应用状态
    applied: bool = Field(description="是否已应用")
    rollback_available: bool = Field(description="是否可回滚")
    
    # 影响评估
    impact_assessment: Dict[str, Any] = Field(description="影响评估")


class ProviderHealthResponse(SuccessResponse[List[ProviderMetrics]]):
    """
    提供商健康状况响应模型
    """
    
    overall_health: str = Field(
        description="整体健康状况",
        regex="^(healthy|warning|critical)$"
    )
    
    unhealthy_providers: List[LLMProviderType] = Field(
        description="不健康的提供商列表"
    )
    
    alerts: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="告警信息"
    )


class ModelCapabilitiesResponse(SuccessResponse[Dict[str, Any]]):
    """
    模型能力响应模型
    """
    
    provider: LLMProviderType = Field(description="提供商")
    model_name: str = Field(description="模型名称")
    
    # 能力信息
    capabilities: List[str] = Field(description="支持的能力")
    limitations: List[str] = Field(description="限制条件")
    
    # 规格信息
    max_context_length: int = Field(description="最大上下文长度")
    supported_languages: List[str] = Field(description="支持的语言")
    pricing: Dict[str, float] = Field(description="定价信息")
    
    # 性能基准
    benchmarks: Optional[Dict[str, float]] = Field(None, description="性能基准")


class RoutingStatsResponse(SuccessResponse[Dict[str, Any]]):
    """
    路由统计响应模型
    """
    
    current_strategy: RoutingStrategy = Field(description="当前路由策略")
    
    # 路由统计
    routing_distribution: Dict[LLMProviderType, float] = Field(
        description="路由分布比例"
    )
    
    agent_routing_stats: Dict[str, Dict[LLMProviderType, int]] = Field(
        description="智能体路由统计"
    )
    
    # 性能指标
    routing_efficiency: float = Field(description="路由效率")
    failover_events: int = Field(description="故障转移事件数")
    
    time_range: Dict[str, datetime] = Field(description="统计时间范围")