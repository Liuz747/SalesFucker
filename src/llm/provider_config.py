"""
多供应商配置模型模块

该模块定义了多LLM供应商系统的配置数据模型，包括供应商凭据、
模型映射、路由规则和成本配置等核心配置结构。

核心功能:
- 供应商凭据安全存储和验证
- 模型能力和配置映射
- 智能路由规则定义
- 多租户配置隔离
- 成本追踪和预算管理
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ProviderType(str, Enum):
    """LLM供应商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class ModelCapability(str, Enum):
    """模型能力枚举"""
    TEXT_GENERATION = "text_generation"
    CHINESE_OPTIMIZATION = "chinese_optimization"
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    MULTIMODAL = "multimodal"
    FAST_RESPONSE = "fast_response"
    COST_EFFECTIVE = "cost_effective"


class ProviderCredentials(BaseModel):
    """供应商凭据配置"""
    provider_type: ProviderType
    api_key: str = Field(..., description="API密钥")
    api_base: Optional[str] = Field(None, description="API基础URL")
    organization: Optional[str] = Field(None, description="组织ID")
    project: Optional[str] = Field(None, description="项目ID")
    region: Optional[str] = Field(None, description="区域设置")
    
    class Config:
        validate_assignment = True


class ModelConfig(BaseModel):
    """模型配置信息"""
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    capabilities: List[ModelCapability] = Field(default_factory=list)
    max_tokens: int = Field(4096, description="最大令牌数")
    temperature: float = Field(0.7, description="温度参数")
    cost_per_1k_tokens: float = Field(0.0, description="每1K令牌成本")
    supports_streaming: bool = Field(True, description="支持流式响应")
    supports_chinese: bool = Field(True, description="支持中文")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('温度参数必须在0.0到2.0之间')
        return v


class ProviderConfig(BaseModel):
    """供应商完整配置"""
    provider_type: ProviderType
    credentials: ProviderCredentials
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    is_enabled: bool = Field(True, description="是否启用")
    priority: int = Field(1, description="优先级(1最高)")
    rate_limit_rpm: int = Field(1000, description="每分钟请求限制")
    rate_limit_tpm: int = Field(100000, description="每分钟令牌限制")
    timeout_seconds: int = Field(30, description="请求超时(秒)")
    retry_attempts: int = Field(3, description="重试次数")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 1:
            raise ValueError('优先级必须大于等于1')
        return v


class AgentProviderMapping(BaseModel):
    """智能体-供应商映射配置"""
    agent_type: str = Field(..., description="智能体类型")
    primary_provider: ProviderType = Field(..., description="主要供应商")
    fallback_providers: List[ProviderType] = Field(default_factory=list)
    model_preferences: Dict[str, str] = Field(default_factory=dict)
    quality_threshold: float = Field(0.8, description="质量阈值")
    
    @validator('quality_threshold')
    def validate_quality_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('质量阈值必须在0.0到1.0之间')
        return v


class RoutingRule(BaseModel):
    """路由规则配置"""
    rule_name: str = Field(..., description="规则名称")
    conditions: Dict[str, Any] = Field(..., description="匹配条件")
    target_provider: ProviderType = Field(..., description="目标供应商")
    priority: int = Field(1, description="规则优先级")
    is_active: bool = Field(True, description="规则是否激活")


class CostConfig(BaseModel):
    """成本配置"""
    daily_budget: Optional[float] = Field(None, description="日预算")
    monthly_budget: Optional[float] = Field(None, description="月预算")
    cost_threshold_warning: float = Field(0.8, description="成本警告阈值")
    cost_threshold_critical: float = Field(0.95, description="成本严重阈值")
    enable_cost_optimization: bool = Field(True, description="启用成本优化")
    
    @validator('cost_threshold_warning', 'cost_threshold_critical')
    def validate_thresholds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('成本阈值必须在0.0到1.0之间')
        return v


class TenantProviderConfig(BaseModel):
    """租户级别供应商配置"""
    tenant_id: str = Field(..., description="租户ID")
    provider_configs: Dict[str, ProviderConfig] = Field(default_factory=dict)
    agent_mappings: Dict[str, AgentProviderMapping] = Field(default_factory=dict)
    routing_rules: List[RoutingRule] = Field(default_factory=list)
    cost_config: CostConfig = Field(default_factory=CostConfig)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GlobalProviderConfig(BaseModel):
    """全局供应商配置"""
    default_providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    tenant_configs: Dict[str, TenantProviderConfig] = Field(default_factory=dict)
    global_settings: Dict[str, Any] = Field(default_factory=dict)
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantProviderConfig]:
        """获取租户配置"""
        return self.tenant_configs.get(tenant_id)
    
    def get_provider_config(
        self, 
        tenant_id: str, 
        provider_type: ProviderType
    ) -> Optional[ProviderConfig]:
        """获取指定租户的供应商配置"""
        tenant_config = self.get_tenant_config(tenant_id)
        if tenant_config:
            return tenant_config.provider_configs.get(provider_type.value)
        return self.default_providers.get(provider_type.value)


class ProviderHealth(BaseModel):
    """供应商健康状态"""
    provider_type: ProviderType
    is_healthy: bool = Field(True, description="是否健康")
    last_check: datetime = Field(default_factory=datetime.now)
    error_rate: float = Field(0.0, description="错误率")
    avg_response_time: float = Field(0.0, description="平均响应时间(ms)")
    rate_limit_remaining: int = Field(1000, description="剩余请求配额")
    consecutive_failures: int = Field(0, description="连续失败次数")
    
    @property
    def status_score(self) -> float:
        """计算健康状态分数(0-1)"""
        if not self.is_healthy:
            return 0.0
        
        # 基于错误率和响应时间计算分数
        error_penalty = min(self.error_rate * 2, 0.5)  # 错误率惩罚
        response_penalty = min(self.avg_response_time / 5000, 0.3)  # 响应时间惩罚
        
        return max(0.0, 1.0 - error_penalty - response_penalty)