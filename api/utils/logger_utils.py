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
    
    应在应用启动时调用
    """
    # 配置根日志器
    logging.basicConfig(
        level=mas_config.LOG_LEVEL,
        format='%(levelname)s:\t  %(asctime)s - %(name)s - Line %(lineno)d - %(message)s'
    )

    # 设置sqlalchemy logger不传播到项目根logger
    logging.getLogger('sqlalchemy').propagate = False
    if mas_config.DEBUG:
        logging.getLogger('httpx').propagate = False
        logging.getLogger('httpcore').propagate = False


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
