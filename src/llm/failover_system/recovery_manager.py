"""
恢复管理模块

负责故障恢复、重试逻辑和性能监控。
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .models import FailureContext, FailoverConfig
from ..base_provider import BaseProvider, LLMRequest, LLMResponse
from ..intelligent_router import RoutingContext
from src.utils import get_component_logger


class RecoveryManager:
    """恢复管理器"""
    
    def __init__(self, config: FailoverConfig):
        """
        初始化恢复管理器
        
        参数:
            config: 故障转移配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "RecoveryManager")
        self.failure_history: List[FailureContext] = []
    
    async def execute_with_retry(
        self,
        provider: BaseProvider,
        request: LLMRequest,
        context: RoutingContext,
        max_retries: Optional[int] = None
    ) -> LLMResponse:
        """
        执行带重试的请求
        
        参数:
            provider: 供应商实例
            request: 请求对象
            context: 路由上下文
            max_retries: 最大重试次数
            
        返回:
            LLMResponse: 响应对象
            
        异常:
            Exception: 重试失败后抛出最后一个异常
        """
        if max_retries is None:
            max_retries = self.config.max_retry_attempts
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 计算重试延迟
                    delay = self._calculate_retry_delay(attempt - 1, last_error)
                    if delay > 0:
                        self.logger.info(f"重试延迟 {delay} 秒，尝试 {attempt}")
                        await asyncio.sleep(delay)
                
                # 执行请求
                response = await provider.generate(request)
                
                # 记录成功
                if attempt > 0:
                    self.logger.info(f"重试成功，供应商: {provider.provider_type}, 尝试次数: {attempt}")
                
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"请求失败，供应商: {provider.provider_type}, 尝试: {attempt}, 错误: {str(e)}")
                
                # 如果是最后一次尝试，直接抛出异常
                if attempt == max_retries:
                    break
                
                # 检查是否应该继续重试
                if not self._should_retry(e, attempt):
                    break
        
        # 所有重试都失败了
        raise last_error
    
    def _calculate_retry_delay(self, attempt: int, error: Exception) -> float:
        """
        计算重试延迟
        
        参数:
            attempt: 当前尝试次数（从0开始）
            error: 上次的错误
            
        返回:
            float: 延迟秒数
        """
        # 基础延迟（指数退避）
        if attempt < len(self.config.retry_delays):
            base_delay = self.config.retry_delays[attempt]
        else:
            # 超出配置范围，使用最后一个值
            base_delay = self.config.retry_delays[-1]
        
        # 根据错误类型调整延迟
        error_message = str(error).lower()
        
        if "rate limit" in error_message:
            # 速率限制错误，使用更长的延迟
            return max(base_delay, 60)  # 至少等待60秒
        elif "timeout" in error_message:
            # 超时错误，适中延迟
            return base_delay * 2
        else:
            # 其他错误，使用基础延迟
            return base_delay
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        参数:
            error: 异常对象
            attempt: 当前尝试次数
            
        返回:
            bool: 是否应该重试
        """
        error_message = str(error).lower()
        
        # 不应该重试的错误类型
        non_retryable_errors = [
            "authentication",
            "unauthorized", 
            "invalid api key",
            "model not found",
            "invalid model"
        ]
        
        for non_retryable in non_retryable_errors:
            if non_retryable in error_message:
                return False
        
        return True
    
    def record_failure(self, failure_context: FailureContext):
        """
        记录故障
        
        参数:
            failure_context: 故障上下文
        """
        self.failure_history.append(failure_context)
        
        # 限制历史记录大小
        if len(self.failure_history) > self.config.max_failure_history:
            self.failure_history = self.failure_history[-self.config.max_failure_history:]
        
        self.logger.debug(f"记录故障: {failure_context.failure_type}, 供应商: {failure_context.provider_type}")
    
    def get_recent_failures(
        self, 
        provider_type: Optional[str] = None,
        time_window_minutes: int = 30
    ) -> List[FailureContext]:
        """
        获取最近的故障记录
        
        参数:
            provider_type: 供应商类型过滤
            time_window_minutes: 时间窗口（分钟）
            
        返回:
            List[FailureContext]: 故障上下文列表
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        recent_failures = [
            failure for failure in self.failure_history
            if failure.timestamp >= cutoff_time
        ]
        
        if provider_type:
            recent_failures = [
                failure for failure in recent_failures
                if failure.provider_type.value == provider_type
            ]
        
        return recent_failures
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """
        获取故障统计信息
        
        返回:
            Dict[str, Any]: 故障统计信息
        """
        if not self.failure_history:
            return {
                "total_failures": 0,
                "recent_failures": 0,
                "failure_by_provider": {},
                "failure_by_type": {}
            }
        
        # 计算最近30分钟的故障
        recent_failures = self.get_recent_failures(time_window_minutes=30)
        
        # 按供应商统计
        failure_by_provider = {}
        for failure in self.failure_history:
            provider = failure.provider_type.value
            failure_by_provider[provider] = failure_by_provider.get(provider, 0) + 1
        
        # 按故障类型统计
        failure_by_type = {}
        for failure in self.failure_history:
            failure_type = failure.failure_type.value
            failure_by_type[failure_type] = failure_by_type.get(failure_type, 0) + 1
        
        return {
            "total_failures": len(self.failure_history),
            "recent_failures": len(recent_failures),
            "failure_by_provider": failure_by_provider,
            "failure_by_type": failure_by_type,
            "oldest_failure": self.failure_history[0].timestamp.isoformat() if self.failure_history else None,
            "newest_failure": self.failure_history[-1].timestamp.isoformat() if self.failure_history else None
        }
    
    def clear_old_failures(self, days: int = 7):
        """
        清理旧的故障记录
        
        参数:
            days: 保留天数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        original_count = len(self.failure_history)
        self.failure_history = [
            failure for failure in self.failure_history
            if failure.timestamp >= cutoff_time
        ]
        
        cleared_count = original_count - len(self.failure_history)
        if cleared_count > 0:
            self.logger.info(f"清理了 {cleared_count} 条旧故障记录")
    
    async def health_check_provider(self, provider: BaseProvider) -> bool:
        """
        检查供应商健康状态
        
        参数:
            provider: 供应商实例
            
        返回:
            bool: 健康状态
        """
        try:
            # 发送简单的健康检查请求
            test_request = LLMRequest(
                messages=[{"role": "user", "content": "ping"}],
                model=provider.get_available_models()[0] if provider.get_available_models() else "default",
                max_tokens=1
            )
            
            await provider.generate(test_request)
            return True
            
        except Exception as e:
            self.logger.warning(f"供应商 {provider.provider_type} 健康检查失败: {str(e)}")
            return False