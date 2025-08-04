"""
成本优化器数据模型

定义成本追踪和分析相关的数据结构。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..provider_config import ProviderType


class CostMetric(str, Enum):
    """成本指标枚举"""
    TOTAL_COST = "total_cost"
    COST_PER_REQUEST = "cost_per_request"
    COST_PER_TOKEN = "cost_per_token"
    DAILY_COST = "daily_cost"
    MONTHLY_COST = "monthly_cost"
    PROVIDER_COST = "provider_cost"
    AGENT_COST = "agent_cost"
    TENANT_COST = "tenant_cost"


class OptimizationType(str, Enum):
    """优化类型枚举"""
    PROVIDER_SWITCH = "provider_switch"     # 供应商切换
    MODEL_DOWNGRADE = "model_downgrade"     # 模型降级
    BATCH_OPTIMIZATION = "batch_optimization" # 批量优化
    CACHE_STRATEGY = "cache_strategy"       # 缓存策略
    USAGE_LIMIT = "usage_limit"            # 使用限制


@dataclass
class CostRecord:
    """成本记录"""
    request_id: str
    provider_type: ProviderType
    model_name: str
    agent_type: Optional[str]
    tenant_id: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    timestamp: datetime
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostAnalysis:
    """成本分析结果"""
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_requests: int
    total_tokens: int
    avg_cost_per_request: float
    avg_cost_per_token: float
    provider_breakdown: Dict[str, float]
    agent_breakdown: Dict[str, float]
    tenant_breakdown: Dict[str, float]
    cost_trends: Dict[str, List[float]]
    optimization_opportunities: List[Dict[str, Any]]


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    optimization_type: OptimizationType
    current_cost: float
    potential_savings: float
    savings_percentage: float
    confidence: float
    description: str
    implementation_details: Dict[str, Any]
    estimated_impact: Dict[str, Any]