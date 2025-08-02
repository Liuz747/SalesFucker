"""
故障转移系统主模块

实现智能的故障检测、分类和自动恢复功能。
支持多种故障转移策略和上下文保持。
"""

import asyncio
import copy
from typing import Optional, List

from .models import FailureContext, FailoverConfig, FailoverAction
from .circuit_breaker import CircuitBreakerManager
from .failure_detector import FailureDetector
from .context_preserver import ContextPreserver
from .recovery_manager import RecoveryManager
from ..base_provider import LLMRequest, LLMResponse, BaseProvider
from ..intelligent_router import IntelligentRouter, RoutingContext, RoutingStrategy
from ..provider_config import ProviderType
from src.utils import get_component_logger, ErrorHandler


class FailoverSystem:
    """
    故障转移系统类
    
    实现智能的故障检测、分类和自动恢复功能。
    支持多种故障转移策略和上下文保持。
    """
    
    def __init__(self, intelligent_router: IntelligentRouter, config: Optional[FailoverConfig] = None):
        """
        初始化故障转移系统
        
        参数:
            intelligent_router: 智能路由器实例
            config: 故障转移配置
        """
        self.router = intelligent_router
        self.config = config or FailoverConfig()
        
        self.logger = get_component_logger(__name__, "FailoverSystem")
        self.error_handler = ErrorHandler("failover_system")
        
        # 初始化子组件
        self.circuit_breaker_manager = CircuitBreakerManager(self.config)
        self.failure_detector = FailureDetector(self.config)
        self.context_preserver = ContextPreserver(self.config)
        self.recovery_manager = RecoveryManager(self.config)
        
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
        attempt_count = 0
        last_error = None
        provider_attempts = []
        
        while attempt_count < self.config.max_retry_attempts:
            try:
                # 更新路由上下文
                current_context = copy.deepcopy(routing_context)
                current_context.retry_count = attempt_count
                current_context.previous_provider = (
                    provider_attempts[-1] if provider_attempts else None
                )
                
                # 选择供应商
                provider = await self.router.route_request(
                    request, current_context, strategy
                )
                
                # 检查断路器状态
                if await self.circuit_breaker_manager.is_circuit_breaker_open(
                    provider.provider_type, current_context
                ):
                    self.logger.warning(f"供应商 {provider.provider_type} 断路器开启，跳过")
                    attempt_count += 1
                    continue
                
                # 记录尝试的供应商
                provider_attempts.append(provider.provider_type)
                
                # 执行请求
                response = await self._execute_request_with_monitoring(
                    provider, request, current_context
                )
                
                # 记录成功
                self.circuit_breaker_manager.record_success(provider.provider_type, current_context)
                
                self.logger.info(f"请求成功，供应商: {provider.provider_type}, 尝试次数: {attempt_count + 1}")
                return response
                
            except Exception as e:
                last_error = e
                attempt_count += 1
                
                # 处理故障
                await self._handle_failure(
                    e, provider.provider_type if 'provider' in locals() else None,
                    request, current_context, attempt_count
                )
                
                self.logger.warning(f"请求失败，尝试次数: {attempt_count}, 错误: {str(e)}")
        
        # 所有尝试都失败了
        self.error_handler.handle_error(last_error, {
            "operation": "execute_with_failover",
            "attempts": attempt_count,
            "providers_tried": provider_attempts
        })
        raise last_error
    
    async def _execute_request_with_monitoring(
        self,
        provider: BaseProvider,
        request: LLMRequest,
        context: RoutingContext
    ) -> LLMResponse:
        """
        执行带监控的请求
        
        参数:
            provider: 供应商实例
            request: 请求对象
            context: 路由上下文
            
        返回:
            LLMResponse: 响应对象
        """
        try:
            # 使用恢复管理器执行请求（包含重试逻辑）
            response = await self.recovery_manager.execute_with_retry(
                provider, request, context, max_retries=1  # 单个供应商级别的重试
            )
            
            return response
            
        except Exception as e:
            # 记录供应商级别的故障
            self.circuit_breaker_manager.record_failure(provider.provider_type, context)
            raise
    
    async def _handle_failure(
        self,
        error: Exception,
        provider_type: Optional[ProviderType],
        request: LLMRequest,
        context: RoutingContext,
        attempt_count: int
    ):
        """
        处理故障
        
        参数:
            error: 异常对象
            provider_type: 供应商类型
            request: 请求对象
            context: 路由上下文
            attempt_count: 尝试次数
        """
        if provider_type is None:
            return
        
        # 创建故障上下文
        failure_context = self.failure_detector.create_failure_context(
            provider_type=provider_type,
            error=error,
            request_id=getattr(request, 'request_id', f"req_{attempt_count}"),
            attempt_count=attempt_count,
            original_request=request,
            routing_context=context
        )
        
        # 记录故障
        self.recovery_manager.record_failure(failure_context)
        
        # 决定故障转移动作
        action = self.failure_detector.determine_failover_action(failure_context)
        
        self.logger.info(f"故障处理: {failure_context.failure_type}, 动作: {action}")
    
    async def prepare_failover_request(
        self,
        original_request: LLMRequest,
        failure_context: FailureContext,
        target_provider: BaseProvider
    ) -> LLMRequest:
        """
        准备故障转移请求
        
        参数:
            original_request: 原始请求
            failure_context: 故障上下文
            target_provider: 目标供应商
            
        返回:
            LLMRequest: 调整后的请求
        """
        return self.context_preserver.preserve_context_for_failover(
            original_request, failure_context, target_provider
        )
    
    async def health_check_all_providers(self) -> dict:
        """
        检查所有供应商的健康状态
        
        返回:
            dict: 健康状态报告
        """
        # 获取所有可用供应商
        providers = await self.router.get_available_providers()
        
        health_status = {}
        for provider in providers:
            try:
                is_healthy = await self.recovery_manager.health_check_provider(provider)
                health_status[provider.provider_type.value] = {
                    "healthy": is_healthy,
                    "last_check": "now"
                }
            except Exception as e:
                health_status[provider.provider_type.value] = {
                    "healthy": False,
                    "error": str(e),
                    "last_check": "now"
                }
        
        return health_status
    
    def get_system_stats(self) -> dict:
        """
        获取系统统计信息
        
        返回:
            dict: 系统统计信息
        """
        return {
            "config": {
                "max_retry_attempts": self.config.max_retry_attempts,
                "context_preservation_enabled": self.config.context_preservation_enabled,
                "circuit_breaker_threshold": self.config.circuit_breaker_threshold
            },
            "circuit_breakers": self.circuit_breaker_manager.get_breaker_stats(),
            "failures": self.recovery_manager.get_failure_stats()
        }
    
    def reset_circuit_breaker(self, provider_type: ProviderType, context: RoutingContext):
        """
        重置断路器状态
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
        """
        self.circuit_breaker_manager.reset_circuit_breaker(provider_type, context)
    
    def clear_failure_history(self, days: int = 7):
        """
        清理故障历史
        
        参数:
            days: 保留天数
        """
        self.recovery_manager.clear_old_failures(days)