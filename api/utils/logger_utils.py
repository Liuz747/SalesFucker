"""
日志工厂模块

提供标准化的日志器创建和管理功能，消除重复的日志初始化代码。

核心功能:
- 统一日志器命名规范
- 组件日志器创建
- 日志混入类
- 全局日志配置管理
"""

import logging
from typing import Optional

from config import mas_config

def configure_logging():
    """
    配置全局日志系统
    
    应该在应用启动时调用一次（在main.py的lifespan函数中）
    """
    # 配置根日志器
    logging.basicConfig(
        level=mas_config.LOG_LEVEL,
        format='%(levelname)s:\t  %(asctime)s - %(name)s - Line %(lineno)d - %(message)s'
    )

    # 设置sqlalchemy logger不传播到项目根logger
    logging.getLogger('sqlalchemy').propagate = False
    logging.getLogger('httpx').propagate = False

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
        logger_name = f"{component_name}"
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