"""
故障转移系统模块

该模块实现了多LLM供应商的自动故障转移和上下文保持功能。
在供应商失败时自动切换到备用供应商，并确保对话上下文的完整性。

核心功能:
- 智能故障检测和分类
- 自动备用供应商选择
- 对话上下文保持和传递
- 断路器模式实现
- 故障恢复和自动重试
"""

from typing import Optional

from .base_provider import LLMRequest, LLMResponse
from .intelligent_router import IntelligentRouter, RoutingContext, RoutingStrategy
from .provider_config import ProviderType
from .failover_system.models import (
    FailureType, 
    FailoverAction, 
    FailureContext, 
    CircuitBreakerState,
    FailoverConfig
)
from .failover_system.failover_system import FailoverSystem as FailoverSystemCore
from src.utils import get_component_logger


class FailoverSystem:
    """
    故障转移系统主类
    
    提供故障转移功能的统一接口，内部使用模块化组件实现。
    这是向后兼容的接口类。
    """
    
    def __init__(self, intelligent_router: IntelligentRouter, config: Optional[FailoverConfig] = None):
        """
        初始化故障转移系统
        
        参数:
            intelligent_router: 智能路由器实例
            config: 故障转移配置
        """
        self.logger = get_component_logger(__name__, "FailoverSystem")
        
        # 使用新的模块化实现
        self.core = FailoverSystemCore(intelligent_router, config)
        
        # 向后兼容属性
        self.router = intelligent_router
        self.config = self.core.config
        self.circuit_breakers = self.core.circuit_breaker_manager.circuit_breakers
        self.failure_history = self.core.recovery_manager.failure_history
        
        # 配置属性（向后兼容）
        self.max_retry_attempts = self.config.max_retry_attempts
        self.retry_delays = self.config.retry_delays
        self.context_preservation_enabled = self.config.context_preservation_enabled
        self.circuit_breaker_threshold = self.config.circuit_breaker_threshold
        self.circuit_breaker_timeout = self.config.circuit_breaker_timeout
        self.circuit_breaker_recovery_success_count = self.config.circuit_breaker_recovery_success_count
        self.max_failure_history = self.config.max_failure_history
        self.failure_patterns = self.config.failure_patterns
        
        self.logger.info("故障转移系统初始化完成")
    
    async def execute_with_failover(
        self,
        request: LLMRequest,
        routing_context: RoutingContext,
        strategy: Optional[RoutingStrategy] = None
    ) -> LLMResponse:
        """
        执行带故障转移的LLM请求
        
        参数:
            request: LLM请求对象
            routing_context: 路由上下文
            strategy: 路由策略
            
        返回:
            LLMResponse: 成功的响应
            
        异常:
            ProviderError: 所有故障转移尝试都失败时抛出
        """
        return await self.core.execute_with_failover(request, routing_context, strategy)
    
    async def health_check_all_providers(self) -> dict:
        """
        检查所有供应商的健康状态
        
        返回:
            dict: 健康状态报告
        """
        return await self.core.health_check_all_providers()
    
    def get_system_stats(self) -> dict:
        """
        获取系统统计信息
        
        返回:
            dict: 系统统计信息
        """
        return self.core.get_system_stats()
    
    def reset_circuit_breaker(self, provider_type: ProviderType, context: RoutingContext):
        """
        重置断路器状态
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
        """
        self.core.reset_circuit_breaker(provider_type, context)
    
    def clear_failure_history(self, days: int = 7):
        """
        清理故障历史
        
        参数:
            days: 保留天数
        """
        self.core.clear_failure_history(days)
    
    # 向后兼容方法
    async def _is_circuit_breaker_open(self, provider_type: ProviderType, context: RoutingContext) -> bool:
        """向后兼容方法"""
        return await self.core.circuit_breaker_manager.is_circuit_breaker_open(provider_type, context)
    
    def _record_circuit_breaker_failure(self, provider_type: ProviderType, context: RoutingContext):
        """向后兼容方法"""
        self.core.circuit_breaker_manager.record_failure(provider_type, context)
    
    def _record_circuit_breaker_success(self, provider_type: ProviderType, context: RoutingContext):
        """向后兼容方法"""
        self.core.circuit_breaker_manager.record_success(provider_type, context)
    
    def _classify_failure(self, error: Exception, provider_type: ProviderType, request_id: str) -> FailureType:
        """向后兼容方法"""
        return self.core.failure_detector.classify_failure(error, provider_type, request_id)
    
    def _create_failure_context(
        self,
        provider_type: ProviderType,
        error: Exception,
        request_id: str,
        attempt_count: int,
        original_request=None,
        routing_context=None
    ) -> FailureContext:
        """向后兼容方法"""
        return self.core.failure_detector.create_failure_context(
            provider_type, error, request_id, attempt_count, original_request, routing_context
        )
    
    def get_failure_stats(self) -> dict:
        """
        获取故障统计信息（向后兼容）
        
        返回:
            dict: 故障统计信息
        """
        return self.core.recovery_manager.get_failure_stats()
    
    def get_recent_failures(self, provider_type: Optional[str] = None, time_window_minutes: int = 30):
        """
        获取最近的故障记录（向后兼容）
        
        参数:
            provider_type: 供应商类型过滤
            time_window_minutes: 时间窗口（分钟）
            
        返回:
            List[FailureContext]: 故障上下文列表
        """
        return self.core.recovery_manager.get_recent_failures(provider_type, time_window_minutes)


# 向后兼容的导出
__all__ = [
    "FailoverSystem",
    "FailureType",
    "FailoverAction", 
    "FailureContext",
    "CircuitBreakerState",
    "FailoverConfig"
]