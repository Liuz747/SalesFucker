"""
智能体核心模块

该模块提供多智能体系统的核心功能和基础组件。

核心组件:
- BaseAgent: 智能体抽象基类
- AgentMessage: 智能体间消息传递
- ConversationState: 对话状态管理
- AgentRegistry: 智能体注册中心
- MultiAgentOrchestrator: 多智能体编排器
- WorkflowBuilder: 工作流构建器
- NodeProcessor: 节点处理器
- ConversationStateManager: 状态管理器
"""

# 核心组件导入
from .base import BaseAgent
from .message import AgentMessage, ConversationState
from .registry import AgentRegistry, agent_registry
from .orchestrator import Orchestrator
from .workflow import WorkflowBuilder
from .node_processor import NodeProcessor
from .state_manager import ConversationStateManager

__all__ = [
    # 核心智能体组件
    "BaseAgent",
    "AgentMessage", 
    "ConversationState",
    "AgentRegistry",
    "agent_registry",
    "Orchestrator",
    "WorkflowBuilder",
    "NodeProcessor",
    "ConversationStateManager"
] 