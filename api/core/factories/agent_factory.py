"""
智能体工厂模块

该模块提供智能体创建的工厂函数，支持批量创建和单个创建。

核心功能:
- 完整智能体集合创建
- 单个智能体创建
- 智能体存储管理
- 简化的智能体访问
"""

from core.agents import (
    BaseAgent,
    ChatAgent,
    IntentAgent,
    SalesAgent,
    SentimentAnalysisAgent,
    # TriggerInactiveAgent,
    # TriggerEngagementAgent
)
from libs.types import AgentNodeType
from utils import get_component_logger

logger = get_component_logger(__name__)


# 工作流节点名 -> 智能体类 映射
AGENT_NODE_MAPPING = {
    AgentNodeType.SENTIMENT: SentimentAnalysisAgent,
    AgentNodeType.SALES: SalesAgent,
    AgentNodeType.INTENT: IntentAgent,
    # AgentNodeType.TRIGGER_INACTIVE: TriggerInactiveAgent,
    # AgentNodeType.TRIGGER_ENGAGEMENT: TriggerEngagementAgent,
    AgentNodeType.CHAT: ChatAgent,
}


def create_agents_set() -> dict[AgentNodeType, BaseAgent]:
    """
    创建完整的Agent集合

    返回:
        dict[AgentNodeType, BaseAgent]: 智能体集合 {AgentNodeType: agent_instance}
    """
    agents: dict[AgentNodeType, BaseAgent] = {}

    # 基于工作流节点名创建智能体集合
    for node_name, agent_class in AGENT_NODE_MAPPING.items():
        agent = agent_class()
        # 使用工作流节点名称作为智能体ID与键，便于工作流直接查找
        agent.agent_id = node_name
        agents[node_name] = agent

    return agents
