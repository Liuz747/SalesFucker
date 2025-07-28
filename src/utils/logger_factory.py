"""
日志工厂模块

提供标准化的日志器创建和管理功能，消除重复的日志初始化代码。

核心功能:
- 统一日志器命名规范
- 组件日志器创建
- 日志混入类
"""

import logging
from typing import Optional


def get_component_logger(component_name: str, identifier: Optional[str] = None) -> logging.Logger:
    """
    获取组件标准化日志器
    
    消除重复的 logging.getLogger(f"{__name__}.{id}") 模式
    
    参数:
        component_name: 组件名称（通常为 __name__）
        identifier: 可选标识符（如tenant_id, agent_id等）
        
    返回:
        logging.Logger: 配置好的日志器
    """
    if identifier:
        logger_name = f"{component_name}.{identifier}"
    else:
        logger_name = component_name
    
    return logging.getLogger(logger_name)


def get_agent_logger(agent_id: str) -> logging.Logger:
    """
    获取智能体专用日志器
    
    参数:
        agent_id: 智能体ID
        
    返回:
        logging.Logger: 智能体日志器
    """
    return get_component_logger("agents", agent_id)


def get_tenant_logger(component: str, tenant_id: str) -> logging.Logger:
    """
    获取租户组件日志器
    
    参数:
        component: 组件名称
        tenant_id: 租户ID
        
    返回:
        logging.Logger: 租户组件日志器
    """
    return get_component_logger(f"{component}", tenant_id)


class LoggerMixin:
    """
    日志混入类
    
    为需要日志功能的类提供标准化的日志器。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
    
    def get_logger(self, identifier: Optional[str] = None) -> logging.Logger:
        """
        获取或创建日志器
        
        参数:
            identifier: 可选标识符
            
        返回:
            logging.Logger: 日志器实例
        """
        if self._logger is None:
            component_name = self.__class__.__module__
            self._logger = get_component_logger(component_name, identifier)
        return self._logger
    
    @property
    def logger(self) -> logging.Logger:
        """日志器属性"""
        return self.get_logger() 