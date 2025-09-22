"""
智能体工厂模块

该模块提供智能体创建的工厂函数，支持批量创建和单个创建。

核心功能:
- 完整智能体集合创建
- 单个智能体创建
- 智能体存储管理
- 简化的智能体访问
"""

from core.agents.base import BaseAgent
from core.agents.compliance import ComplianceAgent
from core.agents.sales import SalesAgent
from core.agents.sentiment import SentimentAnalysisAgent
from core.agents.intent import IntentAnalysisAgent
from core.agents.product import ProductExpertAgent
from core.agents.memory import MemoryAgent
from core.agents.strategy import MarketStrategyCoordinator
from libs.constants import WorkflowConstants
from utils import get_component_logger

logger = get_component_logger(__name__)


# 工作流节点名 -> 智能体类 映射
AGENT_NODE_MAPPING = {
    WorkflowConstants.COMPLIANCE_NODE: ComplianceAgent,
    WorkflowConstants.SENTIMENT_NODE: SentimentAnalysisAgent,
    WorkflowConstants.INTENT_NODE: IntentAnalysisAgent,
    WorkflowConstants.STRATEGY_NODE: MarketStrategyCoordinator,
    WorkflowConstants.SALES_NODE: SalesAgent,
    WorkflowConstants.PRODUCT_NODE: ProductExpertAgent,
    WorkflowConstants.MEMORY_NODE: MemoryAgent,
}


def create_agents_set() -> dict[str, BaseAgent]:
    """
    创建完整的智能体集合

    返回:
        dict[str, BaseAgent]: 智能体集合 {"agent_type": agent_instance}
    """
    agents: dict[str, BaseAgent] = {}

    # 基于工作流节点名创建智能体集合
    for node_name, agent_class in AGENT_NODE_MAPPING.items():
        try:
            agent = agent_class()
            # 使用工作流节点名称作为智能体ID与键，便于工作流直接查找
            agent.agent_id = node_name
            agents[node_name] = agent

        except Exception as e:
            # 如果某个智能体创建失败，记录错误但继续创建其他智能体
            logger.error(f"创建智能体 {node_name} 失败: {e}")
            continue

    return agents
