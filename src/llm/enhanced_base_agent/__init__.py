"""
增强基础智能体子模块

该包包含增强基础智能体的专用组件，提供模块化的智能体功能。
"""

from .agent_config import AgentConfig
from .llm_interface import LLMInterface

__all__ = [
    "AgentConfig",
    "LLMInterface"
]