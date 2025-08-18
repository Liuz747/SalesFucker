"""
错误处理工具模块

提供标准化的错误处理装饰器和类用于统一错误处理。

核心功能:
- 错误处理装饰器
- 降级策略装饰器
- 异常日志记录
- 错误处理器类
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional, Dict
from .time_utils import to_isoformat


def with_error_handling(
        fallback_response: Any = None, 
        log_errors: bool = True,
        reraise: bool = False
    ) -> Callable:
    """
    错误处理装饰器
    
    为函数添加统一的错误处理机制，记录错误并返回降级响应。
    
    参数:
        fallback_response: 发生错误时的降级响应
        log_errors: 是否记录错误日志
        reraise: 是否重新抛出异常
        
    返回:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"错误发生在 {func.__name__}: {e}", exc_info=True)
                
                if reraise:
                    raise
                
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__,
                    "timestamp": to_isoformat(),
                    "fallback_data": fallback_response
                }
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"错误发生在 {func.__name__}: {e}", exc_info=True)
                
                if reraise:
                    raise
                
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__,
                    "timestamp": to_isoformat(),
                    "fallback_data": fallback_response
                }
        
        # 检查是否为异步函数
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_fallback(fallback_handler: Callable[[Exception], Any]):
    """
    降级策略装饰器
    
    当函数执行失败时，调用指定的降级处理函数。
    
    参数:
        fallback_handler: 降级处理函数，接收异常参数
        
    返回:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.warning(f"Fallback triggered for {func.__name__}: {e}")
                return fallback_handler(e)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.warning(f"Fallback triggered for {func.__name__}: {e}")
                return fallback_handler(e)
        
        # 检查是否为异步函数
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ErrorHandler:
    """
    错误处理器类
    
    提供集中化的错误处理逻辑。
    """
    
    def __init__(self, component_name: str):
        """
        初始化错误处理器
        
        参数:
            component_name: 组件名称
        """
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理错误并返回标准化错误信息
        
        参数:
            error: 异常对象
            context: 错误上下文
            
        返回:
            Dict[str, Any]: 标准化错误信息
        """
        error_info = {
            "error": str(error),
            "error_type": type(error).__name__,
            "component": self.component_name,
            "timestamp": to_isoformat()
        }
        
        if context:
            error_info["context"] = context
        
        self.logger.error(
            f"Error in {self.component_name}: {error}",
            exc_info=True,
            extra={"error_context": context}
        )
        
        return error_info
    
    async def safe_execute(self, func: Callable, *args, 
                          fallback_result: Any = None, **kwargs) -> Any:
        """
        安全执行函数，自动处理异常
        
        参数:
            func: 要执行的函数
            fallback_result: 失败时的回退结果
            *args, **kwargs: 函数参数
            
        返回:
            Any: 执行结果或回退结果
        """
        try:
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, {"function": func.__name__, "args": str(args)})
            return fallback_result 