"""
Sales Agent Module - 极简架构

专注于情感驱动的销售响应生成。
与 Sentiment Agent 紧密协同，提供个性化的客户服务。

核心组件:
- SalesAgent: 主协调器
- SalesResponseGenerator: 响应生成引擎

设计理念:
- 极简主义架构
- 情感驱动交互
- 专注核心职责
- 高度可维护性
"""

from .agent import SalesAgent, SalesResponseGenerator

__all__ = [
    # 主要智能体
    "SalesAgent",

    # 核心组件
    "SalesResponseGenerator"
]