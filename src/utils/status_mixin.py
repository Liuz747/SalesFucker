"""
状态管理混入模块

提供标准化的状态检查和响应格式，消除重复的状态方法。

核心功能:
- 统一状态响应格式
- 健康检查标准化
- 状态混入类
"""

from typing import Dict, Any, Optional
from .time_utils import format_timestamp
from .constants import StatusConstants


class StatusMixin:
    """
    状态管理混入类
    
    为需要状态检查功能的类提供标准化的状态管理方法。
    消除重复的状态检查代码。
    """
    
    def create_status_response(
            self, 
            status_data: Dict[str, Any], 
            component_name: Optional[str] = None
        ) -> Dict[str, Any]:
        """
        创建标准化状态响应
        
        参数:
            status_data: 状态数据字典
            component_name: 可选的组件名称
            
        返回:
            Dict[str, Any]: 标准化状态响应
        """
        response = {
            **status_data,
            "timestamp": format_timestamp(),
            "component": component_name or self.__class__.__name__
        }
        
        return response
    
    def create_health_response(
            self, 
            health_status: str, 
            metrics: Dict[str, Any] = None,
            details: Dict[str, Any] = None
        ) -> Dict[str, Any]:
        """
        创建标准化健康检查响应
        
        参数:
            health_status: 健康状态（healthy/warning/critical）
            metrics: 可选的指标数据
            details: 可选的详细信息
            
        返回:
            Dict[str, Any]: 健康检查响应
        """
        response = {
            "status": health_status,
            "timestamp": format_timestamp(),
            "component": self.__class__.__name__
        }
        
        if metrics:
            response["metrics"] = metrics
            
        if details:
            response["details"] = details
            
        return response
    
    def determine_health_status(
            self,
            error_rate: float,
            warning_threshold: float = 10.0,
            critical_threshold: float = 20.0
    ) -> str:
        """
        根据错误率确定健康状态
        
        参数:
            error_rate: 错误率百分比
            warning_threshold: 警告阈值
            critical_threshold: 严重阈值
            
        返回:
            str: 健康状态
        """
        if error_rate >= critical_threshold:
            return StatusConstants.CRITICAL
        elif error_rate >= warning_threshold:
            return StatusConstants.WARNING
        else:
            return StatusConstants.HEALTHY
    
    def create_error_response(
            self, 
            error: Exception, 
            context: Dict[str, Any] = None
        ) -> Dict[str, Any]:
        """
        创建标准化错误响应
        
        参数:
            error: 异常对象
            context: 可选的错误上下文
            
        返回:
            Dict[str, Any]: 错误响应
        """
        response = {
            "error": str(error),
            "error_type": type(error).__name__,
            "component": self.__class__.__name__,
            "timestamp": format_timestamp()
        }
        
        if context:
            response["context"] = context
            
        return response 