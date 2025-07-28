"""
智能体核心模块 - 优化版本

该模块提供多智能体系统的核心功能和基础组件。
包含标准化工具和优化后的核心类。

核心组件:
- BaseAgent: 智能体抽象基类
- AgentMessage, ConversationState: 消息和状态管理
- AgentRegistry: 智能体注册中心
- MultiAgentOrchestrator: 多智能体编排器
- WorkflowBuilder: 工作流构建器
- NodeProcessor: 节点处理器
- ConversationStateManager: 状态管理器

工具模块:
- 时间处理工具
- 日志管理工具
- 状态管理混入
- 错误处理装饰器
- 系统常量定义
"""

# 核心组件导入
from .base_agent import BaseAgent
from .message import AgentMessage, ConversationState
from .registry import AgentRegistry, agent_registry
from .orchestrator import MultiAgentOrchestrator
from .workflow import WorkflowBuilder
from .workflow_nodes import NodeProcessor
from .state_manager import ConversationStateManager

# 工具模块导入
from src.utils import (
    # 时间工具
    get_current_timestamp,
    get_processing_time_ms,
    TimestampMixin,
    
    # 日志工具
    get_component_logger,
    LoggerMixin,
    
    # 状态管理
    StatusMixin,
    
    # 错误处理
    with_error_handling,
    with_fallback,
    ErrorHandler,
    
    # 常量
    StatusConstants,
    ProcessingConstants,
    MessageConstants,
    WorkflowConstants,
    AgentConstants,
    ErrorConstants,
    ConfigConstants
)

__all__ = [
    # 核心智能体组件
    "BaseAgent",
    "AgentMessage", 
    "ConversationState",
    "AgentRegistry",
    "agent_registry",
    "MultiAgentOrchestrator",
    "WorkflowBuilder",
    "NodeProcessor",
    "ConversationStateManager",
    
    # 时间工具
    "get_current_timestamp",
    "get_processing_time_ms", 
    "TimestampMixin",
    
    # 日志工具
    "get_component_logger",
    "LoggerMixin",
    
    # 状态管理
    "StatusMixin",
    
    # 错误处理
    "with_error_handling",
    "with_fallback",
    "ErrorHandler",
    
    # 系统常量
    "StatusConstants",
    "ProcessingConstants", 
    "MessageConstants",
    "WorkflowConstants",
    "AgentConstants",
    "ErrorConstants",
    "ConfigConstants"
] 