"""
智能体工厂模块

该模块提供智能体创建的工厂函数，支持批量创建和单个创建。

核心功能:
- 完整智能体集合创建
- 单个智能体创建
- 智能体存储管理
- 简化的智能体访问
"""

from typing import Dict, Optional
from core.agents.base import BaseAgent
from core.agents.compliance import ComplianceAgent
from core.agents.sales import SalesAgent
from core.agents.sentiment import SentimentAnalysisAgent
from core.agents.intent import IntentAnalysisAgent
from core.agents.product import ProductExpertAgent
from core.agents.memory import MemoryAgent
from core.agents.strategy import MarketStrategyCoordinator
from core.agents.proactive import ProactiveAgent
from core.agents.suggestion import AISuggestionAgent
from libs.constants import WorkflowConstants


# Global agent storage - simple dictionary for agent lookup
_global_agents: Dict[str, BaseAgent] = {}

# 智能体类型映射
AGENT_TYPE_MAPPING = {
    "compliance": ComplianceAgent,
    "sentiment": SentimentAnalysisAgent,
    "intent": IntentAnalysisAgent,
    "sales": SalesAgent,
    "product": ProductExpertAgent,
    "memory": MemoryAgent,
    "strategy": MarketStrategyCoordinator,
    "proactive": ProactiveAgent,
    "suggestion": AISuggestionAgent,
}


def create_agent_set() -> Dict[str, BaseAgent]:
    """
    创建完整的智能体集合

    返回:
        Dict[str, BaseAgent]: 智能体集合 {"agent_type": agent_instance}
    """
    agents = {}

    # 映射简单agent类型到工作流节点名称
    workflow_mappings = {
        "compliance": WorkflowConstants.COMPLIANCE_NODE,
        "sentiment": WorkflowConstants.SENTIMENT_NODE,
        "intent": WorkflowConstants.INTENT_NODE,
        "strategy": WorkflowConstants.STRATEGY_NODE,
        "sales": WorkflowConstants.SALES_NODE,
        "product": WorkflowConstants.PRODUCT_NODE,
        "memory": WorkflowConstants.MEMORY_NODE,
    }

    # 创建完整的9智能体系统
    for agent_type, agent_class in AGENT_TYPE_MAPPING.items():
        try:
            agent = agent_class()  # No parameters - agent_id auto-derived
            agent.agent_id = agent_type  # Override with proper ID from mapping
            agents[agent_type] = agent

            # 在全局注册表中注册智能体
            _global_agents[agent_type] = agent

            # 如果有对应的工作流节点名称，也注册该名称
            if agent_type in workflow_mappings:
                workflow_node = workflow_mappings[agent_type]
                _global_agents[workflow_node] = agent

        except Exception as e:
            # 如果某个智能体创建失败，记录错误但继续创建其他智能体
            print(f"警告: 创建智能体 {agent_type} 失败: {e}")
            continue

    return agents


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """
    根据ID获取智能体实例

    参数:
        agent_id: 智能体唯一标识符

    返回:
        Optional[BaseAgent]: 智能体实例，不存在时返回None
    """
    return _global_agents.get(agent_id)
