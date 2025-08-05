"""
智能体工厂模块

该模块提供智能体创建的工厂函数，支持批量创建和单个创建。

核心功能:
- 完整智能体集合创建
- 单个智能体创建
- 智能体注册管理
- 多租户隔离支持
"""

from typing import Dict, Optional
from src.agents.base import BaseAgent, agent_registry
from src.agents.compliance import ComplianceAgent
from src.agents.sales import SalesAgent
from src.agents.sentiment import SentimentAnalysisAgent
from src.agents.intent import IntentAnalysisAgent
from src.agents.product import ProductExpertAgent
from src.agents.memory import MemoryAgent
from src.agents.strategy import MarketStrategyCoordinator
from src.agents.proactive import ProactiveAgent
from src.agents.suggestion import AISuggestionAgent


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


def create_agent_set(tenant_id: str, auto_register: bool = True) -> Dict[str, BaseAgent]:
    """
    为指定租户创建完整的智能体集合
    
    参数:
        tenant_id: 租户标识符，用于多租户隔离
        auto_register: 是否自动注册到全局注册中心，默认True
        
    返回:
        Dict[str, BaseAgent]: 智能体集合 {"agent_type": agent_instance}
    """
    agents = {}
    
    # 创建完整的9智能体系统
    for agent_type, agent_class in AGENT_TYPE_MAPPING.items():
        try:
            agent = agent_class(tenant_id)
            agents[agent_type] = agent
        except Exception as e:
            # 如果某个智能体创建失败，记录错误但继续创建其他智能体
            print(f"警告: 创建智能体 {agent_type} 失败: {e}")
            continue
    
    # 可选：在全局注册中心注册智能体
    if auto_register:
        for agent in agents.values():
            try:
                agent_registry.register_agent(agent)
            except Exception as e:
                print(f"警告: 注册智能体 {agent.agent_id} 失败: {e}")
    
    return agents


def create_single_agent(
    agent_type: str, 
    tenant_id: str, 
    auto_register: bool = True
) -> Optional[BaseAgent]:
    """
    创建单个智能体实例
    
    参数:
        agent_type: 智能体类型 (compliance, sentiment, intent, sales, etc.)
        tenant_id: 租户标识符
        auto_register: 是否自动注册到全局注册中心，默认True
        
    返回:
        Optional[BaseAgent]: 智能体实例，创建失败时返回None
    """
    if agent_type not in AGENT_TYPE_MAPPING:
        print(f"错误: 不支持的智能体类型 '{agent_type}'")
        print(f"支持的类型: {list(AGENT_TYPE_MAPPING.keys())}")
        return None
    
    try:
        agent_class = AGENT_TYPE_MAPPING[agent_type]
        agent = agent_class(tenant_id)
        
        # 可选：注册到全局注册中心
        if auto_register:
            agent_registry.register_agent(agent)
        
        return agent
        
    except Exception as e:
        print(f"错误: 创建智能体 {agent_type} 失败: {e}")
        return None


def get_available_agent_types() -> list:
    """
    获取所有可用的智能体类型
    
    返回:
        list: 可用的智能体类型列表
    """
    return list(AGENT_TYPE_MAPPING.keys())


def cleanup_tenant_agents(tenant_id: str) -> int:
    """
    清理指定租户的所有智能体
    
    参数:
        tenant_id: 要清理的租户ID
        
    返回:
        int: 清理的智能体数量
    """
    return agent_registry.cleanup_tenant(tenant_id)