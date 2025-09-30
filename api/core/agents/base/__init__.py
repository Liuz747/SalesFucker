"""
智能体核心模块

该模块提供多智能体系统的基础智能体组件。

核心组件:
- BaseAgent: 智能体抽象基类
- AgentMessage: 智能体间消息传递
- ThreadState: 对话状态管理

注意: LangGraph工作流组件现在位于 src.core 模块中。
"""

# 核心智能体组件导入
from .agent import BaseAgent
from .message import AgentMessage
from .response_parser import parse_json_response

__all__ = [
    # 核心智能体组件
    "BaseAgent",
    "AgentMessage",
    "parse_json_response"
] 