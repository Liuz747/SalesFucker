"""
多智能体系统实现

该包包含化妆品行业数字营销的多智能体系统的所有专业智能体:
- 合规审查智能体 (Compliance Review Agent)
- 情感分析智能体 (Sentiment Analysis Agent)  
- 意图分析智能体 (Intent Analysis Agent)
- 销售智能体 (Sales Agent)
- 产品专家智能体 (Product Expert Agent)
- 记忆管理智能体 (Memory Agent)
- 市场策略集群 (Market Strategy Cluster: Premium, Budget, Youth, Mature)
- 主动营销智能体 (Proactive Agent)
- AI建议智能体 (AI Suggestion Agent)

模块组织采用trunk-based development最佳实践：
- core/: 核心基础组件和架构
- compliance/: 合规检查相关模块
- sales/: 销售智能体相关模块
- (更多模块按需扩展)
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
from .intent import IntentAnalysisAgent
from .product import ProductExpertAgent
from .memory import MemoryAgent
from .strategy import MarketStrategyCoordinator
from .proactive import ProactiveAgent
from .suggestion import AISuggestionAgent

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
    "IntentAnalysisAgent",
    "ProductExpertAgent",
    "MemoryAgent",
    "MarketStrategyCoordinator",
    "ProactiveAgent",
    "AISuggestionAgent",
] 