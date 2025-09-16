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
    
    # 创建完整的9智能体系统
    for agent_type, agent_class in AGENT_TYPE_MAPPING.items():
        try:
            agent = agent_class()  # No parameters - agent_id auto-derived
            agent.agent_id = agent_type  # Override with proper ID from mapping
            agents[agent_type] = agent
            _global_agents[agent_type] = agent  # Store in global dict
        except Exception as e:
            # 如果某个智能体创建失败，记录错误但继续创建其他智能体
            print(f"警告: 创建智能体 {agent_type} 失败: {e}")
            continue
    
    return agents


def create_single_agent(agent_type: str) -> Optional[BaseAgent]:
    """
    创建单个智能体实例

    参数:
        agent_type: 智能体类型 (compliance, sentiment, intent, sales, etc.)

    返回:
        Optional[BaseAgent]: 智能体实例，创建失败时返回None
    """
    if agent_type not in AGENT_TYPE_MAPPING:
        print(f"错误: 不支持的智能体类型 '{agent_type}'")
        print(f"支持的类型: {list(AGENT_TYPE_MAPPING.keys())}")
        return None
    
    try:
        agent_class = AGENT_TYPE_MAPPING[agent_type]
        agent = agent_class()  # No parameters - agent_id auto-derived
        agent.agent_id = agent_type  # Override with proper ID from mapping
        _global_agents[agent_type] = agent  # Store in global dict
        return agent

    except Exception as e:
        print(f"错误: 创建智能体 {agent_type} 失败: {e}")
        return None


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """
    根据ID获取智能体实例

    参数:
        agent_id: 智能体唯一标识符

    返回:
        Optional[BaseAgent]: 智能体实例，不存在时返回None
    """
    return _global_agents.get(agent_id)


def get_all_agents() -> Dict[str, BaseAgent]:
    """
    获取所有已创建的智能体

    返回:
        Dict[str, BaseAgent]: 所有智能体的副本
    """
    return _global_agents.copy()


def get_available_agent_types() -> list:
    """
    获取所有可用的智能体类型
    
    返回:
        list: 可用的智能体类型列表
    """
    return list(AGENT_TYPE_MAPPING.keys())


def cleanup_all_agents() -> int:
    """
    清理所有智能体

    返回:
        int: 清理的智能体数量
    """
    count = len(_global_agents)
    _global_agents.clear()
    return count