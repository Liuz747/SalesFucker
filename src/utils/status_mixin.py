"""
状态管理混入模块

提供标准化的状态检查和响应格式，消除重复的状态方法。

核心功能:
- 统一状态响应格式
- 健康检查标准化
- 状态混入类
"""

from typing import Dict, Any
from .time_utils import format_timestamp


class StatusMixin:
    """
    状态管理混入类
    
    提供纯格式化工具，用于标准化API响应格式。
    不包含业务逻辑或数据收集，只做响应格式化。
    """
    
    def create_status_response(self, status_data: Dict[str, Any], component_name: str = None) -> Dict[str, Any]:
        """创建标准化状态响应"""
        return {
            **status_data,
            "timestamp": format_timestamp(),
            "component": component_name or self.__class__.__name__
        }
    
    def create_metrics_response(self, metrics: Dict[str, Any] = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建指标数据响应（不包含主观状态判断）"""
        response = {
            "timestamp": format_timestamp(),
            "component": self.__class__.__name__
        }
        if metrics:
            response["metrics"] = metrics
        if details:
            response["details"] = details
        return response
    
    def create_error_response(self, error_message: str, error_type: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建标准化错误响应"""
        response = {
            "error": error_message,
            "timestamp": format_timestamp(),
            "component": self.__class__.__name__
        }
        if error_type:
            response["error_type"] = error_type
        if context:
            response["context"] = context
        return response
    
    def create_success_response(self, data: Dict[str, Any] = None, message: str = None) -> Dict[str, Any]:
        """创建标准化成功响应"""
        response = {
            "success": True,
            "timestamp": format_timestamp(),
            "component": self.__class__.__name__
        }
        if message:
            response["message"] = message
        if data:
            response["data"] = data
        return response
    
 