"""
Sales Agent Module - 智能匹配提示词 + 记忆系统

基于 SentimentAgent 输出的 matched_prompt，结合记忆上下文生成个性化销售回复。
移除复杂的产品推荐逻辑，专注于核心对话生成。

核心组件:
- SalesAgent: 主协调器（简化版）

设计理念:
- 极简主义架构
- 情感驱动交互
- 记忆驱动个性化
- 配置驱动提示词
"""

from .agent import SalesAgent

__all__ = [
    # 主要智能体
    "SalesAgent"
]