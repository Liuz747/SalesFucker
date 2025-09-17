"""
系统工厂模块

该模块提供整个MAS系统的工厂模式实现，支持各种组件的创建和管理。

工厂类型:
- Agent Factories: 智能体创建工厂
- System Factories: 系统级组件工厂  
- Provider Factories: LLM提供商工厂
- Memory Factories: 存储系统工厂

核心功能:
- 标准化组件创建流程
- 依赖注入和配置管理
- 多租户资源隔离
- 系统初始化自动化
"""

# 智能体工厂
from .agent_factory import (
    create_agent_set,
    create_single_agent,
    get_available_agent_types
)

# 系统工厂  
from .system_factory import (
    get_orchestrator,
    create_tenant_system,
    get_system_status
)

__all__ = [
    # 智能体工厂函数
    "create_agent_set",
    "create_single_agent", 
    "get_available_agent_types",
    
    # 系统工厂函数
    "get_orchestrator",
    "create_tenant_system", 
    "get_system_status"
]