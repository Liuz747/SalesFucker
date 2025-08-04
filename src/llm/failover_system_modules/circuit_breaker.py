"""
断路器管理模块

负责断路器状态管理和自动恢复机制。
"""

import asyncio
from typing import Dict
from datetime import datetime, timedelta

from .models import CircuitBreakerState, FailoverConfig
from ..provider_config import ProviderType
from ..intelligent_router import RoutingContext
from src.utils import get_component_logger


class CircuitBreakerManager:
    """断路器管理器"""
    
    def __init__(self, config: FailoverConfig):
        """
        初始化断路器管理器
        
        参数:
            config: 故障转移配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "CircuitBreakerManager")
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
    
    def get_breaker_key(self, provider_type: ProviderType, context: RoutingContext) -> str:
        """获取断路器键值"""
        # 基于供应商类型和租户ID构建键值
        return f"{provider_type}_{context.tenant_id}"
    
    async def is_circuit_breaker_open(
        self, 
        provider_type: ProviderType, 
        context: RoutingContext
    ) -> bool:
        """
        检查断路器是否开启
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
            
        返回:
            bool: 断路器是否开启
        """
        breaker_key = self.get_breaker_key(provider_type, context)
        breaker = self.circuit_breakers.get(breaker_key)
        
        if not breaker:
            return False
        
        # 检查是否到了尝试恢复的时间
        if breaker.is_open and breaker.next_attempt_time:
            if datetime.now() >= breaker.next_attempt_time:
                # 进入半开状态
                breaker.is_open = False
                breaker.success_count_after_half_open = 0
                self.logger.info(f"断路器 {breaker_key} 进入半开状态")
                return False
        
        return breaker.is_open
    
    def record_failure(self, provider_type: ProviderType, context: RoutingContext):
        """
        记录故障，更新断路器状态
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
        """
        breaker_key = self.get_breaker_key(provider_type, context)
        breaker = self.circuit_breakers.get(breaker_key)
        
        if not breaker:
            breaker = CircuitBreakerState()
            self.circuit_breakers[breaker_key] = breaker
        
        breaker.failure_count += 1
        breaker.last_failure_time = datetime.now()
        breaker.success_count_after_half_open = 0
        
        # 检查是否需要开启断路器
        if breaker.failure_count >= self.config.circuit_breaker_threshold:
            breaker.is_open = True
            breaker.next_attempt_time = datetime.now() + timedelta(
                seconds=self.config.circuit_breaker_timeout
            )
            self.logger.warning(
                f"断路器 {breaker_key} 开启，失败次数: {breaker.failure_count}"
            )
    
    def record_success(self, provider_type: ProviderType, context: RoutingContext):
        """
        记录成功，更新断路器状态
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
        """
        breaker_key = self.get_breaker_key(provider_type, context)
        breaker = self.circuit_breakers.get(breaker_key)
        
        if not breaker:
            return
        
        if breaker.is_open:
            # 半开状态下的成功
            breaker.success_count_after_half_open += 1
            
            if breaker.success_count_after_half_open >= self.config.circuit_breaker_recovery_success_count:
                # 完全恢复
                breaker.is_open = False
                breaker.failure_count = 0
                breaker.success_count_after_half_open = 0
                breaker.next_attempt_time = None
                self.logger.info(f"断路器 {breaker_key} 完全恢复")
        else:
            # 正常状态下的成功，重置失败计数
            breaker.failure_count = max(0, breaker.failure_count - 1)
    
    def get_breaker_stats(self) -> Dict[str, Dict]:
        """获取所有断路器状态统计"""
        stats = {}
        for key, breaker in self.circuit_breakers.items():
            stats[key] = {
                "is_open": breaker.is_open,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
                "next_attempt_time": breaker.next_attempt_time.isoformat() if breaker.next_attempt_time else None,
                "success_count_after_half_open": breaker.success_count_after_half_open
            }
        return stats
    
    def reset_circuit_breaker(self, provider_type: ProviderType, context: RoutingContext):
        """
        重置断路器状态
        
        参数:
            provider_type: 供应商类型
            context: 路由上下文
        """
        breaker_key = self.get_breaker_key(provider_type, context)
        if breaker_key in self.circuit_breakers:
            del self.circuit_breakers[breaker_key]
            self.logger.info(f"断路器 {breaker_key} 已重置")