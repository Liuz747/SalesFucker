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
from .core import (
    BaseAgent,
    AgentMessage,
    ConversationState,
    AgentRegistry,
    MultiAgentOrchestrator,
    agent_registry,
    MessagePriority,
    MessageType,
    ComplianceStatus,
    MarketStrategy
)

# 导入专业智能体
from .compliance import ComplianceAgent, ComplianceRule, ComplianceRuleSet
from .sales import SalesAgent

# 导出所有智能体类和核心组件
__all__ = [
    # 核心基础组件
    "BaseAgent",
    "AgentMessage", 
    "ConversationState",
    "AgentRegistry",
    "MultiAgentOrchestrator",
    "agent_registry",
    "MessagePriority",
    "MessageType",
    "ComplianceStatus",
    "MarketStrategy",
    
    # 专业智能体实现
    "ComplianceAgent",
    "ComplianceRule",
    "ComplianceRuleSet",
    "SalesAgent",
    
    # 工厂函数
    "create_agent_set",
    "get_orchestrator"
]

# 智能体工厂函数，便于租户实例化
def create_agent_set(tenant_id: str) -> dict:
    """
    为指定租户创建完整的智能体集合
    
    参数:
        tenant_id: 租户标识符，用于多租户隔离
        
    返回:
        dict: 智能体集合 {"agent_type": agent_instance}
    """
    agents = {}
    
    # 创建核心智能体
    agents["compliance"] = ComplianceAgent(tenant_id)
    agents["sales"] = SalesAgent(tenant_id)
    
    # 在全局注册中心注册智能体
    for agent in agents.values():
        agent_registry.register_agent(agent)
    
    return agents

# 获取租户编排器的工具函数
def get_orchestrator(tenant_id: str) -> MultiAgentOrchestrator:
    """
    获取或创建指定租户的智能体编排器
    
    参数:
        tenant_id: 租户标识符
        
    返回:
        MultiAgentOrchestrator: 多智能体编排器实例
    """
    return MultiAgentOrchestrator(tenant_id) 