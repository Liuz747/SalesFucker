"""
智能路由器数据模型

定义路由相关的数据结构。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..provider_config import ProviderType
from ..base_provider import BaseProvider


class RoutingStrategy(str, Enum):
    """路由策略枚举"""
    PERFORMANCE_FIRST = "performance_first"  # 性能优先
    COST_FIRST = "cost_first"               # 成本优先
    BALANCED = "balanced"                   # 平衡策略
    AGENT_OPTIMIZED = "agent_optimized"     # 智能体优化
    CHINESE_OPTIMIZED = "chinese_optimized" # 中文优化


@dataclass
class RoutingContext:
    """路由上下文数据"""
    agent_type: Optional[str] = None
    tenant_id: Optional[str] = None
    conversation_id: Optional[str] = None
    content_language: Optional[str] = None
    has_multimodal: bool = False
    urgency_level: str = "medium"  # low/medium/high
    cost_priority: float = 0.5     # 0=最低成本, 1=不考虑成本
    quality_threshold: float = 0.8
    previous_provider: Optional[ProviderType] = None
    retry_count: int = 0


@dataclass
class ProviderScore:
    """供应商评分"""
    provider: BaseProvider
    total_score: float
    performance_score: float
    cost_score: float
    capability_score: float
    health_score: float
    load_score: float
    details: Dict[str, Any]