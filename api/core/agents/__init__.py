"""
多智能体系统实现

该包包含行业数字营销的多智能体系统的所有专业智能体:
- 合规审查智能体 (Compliance Review Agent)
- 情感与意图分析智能体 (Sentiment & Intent Analysis Agent)
- 销售智能体 (Sales Agent)
- 产品专家智能体 (Product Expert Agent)
"""

# 导入核心组件
from .base import (
    BaseAgent,
    AgentMessage
)

# 导入专业智能体
from .compliance import ComplianceAgent, ComplianceRule, ComplianceRuleManager
from .sales import SalesAgent
from .sentiment import SentimentAnalysisAgent
from .product import ProductExpertAgent

# 导出所有智能体类和核心组件
__all__ = [
    # 核心基础组件
    "BaseAgent",
    "AgentMessage",

    # 专业智能体实现
    "ComplianceAgent",
    "ComplianceRule",
    "ComplianceRuleManager",
    "SalesAgent",
    "SentimentAnalysisAgent",
    "ProductExpertAgent"
] 