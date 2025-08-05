"""
智能体核心模块

该模块提供多智能体系统的基础智能体组件。

核心组件:
- BaseAgent: 智能体抽象基类
- AgentMessage: 智能体间消息传递
- ConversationState: 对话状态管理
- AgentRegistry: 智能体注册中心

注意: LangGraph工作流组件现在位于 src.core 模块中。
"""

# 核心智能体组件导入
from .agent import BaseAgent
from .message import AgentMessage, ConversationState
from .registry import AgentRegistry, agent_registry

__all__ = [
    # 核心智能体组件
    "BaseAgent",
    "AgentMessage", 
    "ConversationState",
    "AgentRegistry",
    "agent_registry"
] 