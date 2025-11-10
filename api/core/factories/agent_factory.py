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
from core.agents.sales import SalesAgent
from core.agents.sentiment import SentimentAnalysisAgent
from core.agents.chat.agent import ChatAgent
from libs.constants import AgentNodes
from utils import get_component_logger

logger = get_component_logger(__name__)


class FallbackAgent(BaseAgent):
    """降级智能体 - 用于处理其他智能体创建失败的情况"""

    async def process_conversation(self, state: dict) -> dict:
        """提供基本的对话状态传递"""
        self.logger.warning(f"降级智能体 {self.agent_id} 正在处理对话")
        # 简单地返回原状态，不进行任何修改
        return state


# 工作流节点名 -> 智能体类 映射
AGENT_NODE_MAPPING = {
    AgentNodes.SENTIMENT_NODE: SentimentAnalysisAgent,
    AgentNodes.SALES_NODE: SalesAgent,
    "chat_agent": ChatAgent,
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
            logger.info(f"智能体 {node_name} 创建成功")

        except Exception as e:
            # 如果某个智能体创建失败，记录错误并创建一个基础降级智能体
            logger.error(f"创建智能体 {node_name} 失败: {e}")

            # 创建基础降级智能体作为占位符
            try:
                fallback_agent = FallbackAgent()
                fallback_agent.agent_id = node_name
                fallback_agent._is_fallback = True  # 标记为降级智能体
                agents[node_name] = fallback_agent
                logger.warning(f"为 {node_name} 创建了降级智能体")
            except Exception as fallback_error:
                logger.error(f"创建降级智能体 {node_name} 也失败了: {fallback_error}")
                # 完全失败的情况下，至少确保字典中有这个键，值为 None
                agents[node_name] = None

    return agents
