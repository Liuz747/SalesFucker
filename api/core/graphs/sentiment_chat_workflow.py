"""
情感驱动的聊天工作流

实现基于情感分析的聊天对话流程。先进行情感分析，然后将分析结果
传递给聊天智能体，以提供更加个性化和情感化的回复。

工作流程：
1. Sentiment Agent - 分析客户的情感状态和购买意图
2. Chat Agent - 基于情感分析结果生成个性化回复
"""

from typing import Optional
from collections.abc import Callable

from langgraph.graph import StateGraph

from core.agents.base import BaseAgent
from core.entities import WorkflowExecutionModel
from utils import get_component_logger
from libs.constants import AgentNodes
from .base_workflow import BaseWorkflow
from core.agents.base import BaseAgent


logger = get_component_logger(__name__)

class SentimentChatWorkflow(BaseWorkflow):
    """
    情感驱动的聊天工作流

    实现简化的聊天对话流程：
    1. 情感分析节点 - 分析客户情感和意图
    2. 聊天节点 - 基于情感分析结果生成回复

    特点：
    - 精简的两节点流程
    - 情感分析结果直接影响回复生成
    - 适合快速响应场景
    """

    def __init__(self, agents: dict[str, "BaseAgent"]):
        """
        初始化情感聊天工作流

        参数:
            agents: 智能体字典，需要包含 sentiment 和 sales 节点
        """
        self.agents = agents

    def _register_nodes(self, graph: StateGraph):
        """
        注册工作流节点

        参数:
            graph: 要注册节点的状态图
        """
        # 注册两个核心节点
        node_mappings = [
            AgentNodes.SENTIMENT_NODE,
            AgentNodes.SALES_NODE,  # 作为chat agent使用
        ]

        # 注册所有节点处理函数
        for node_name in node_mappings:
            graph.add_node(node_name, self._create_agent_node(node_name))

        logger.debug(f"已注册 {len(node_mappings)} 个工作流节点")

    def _define_edges(self, graph: StateGraph):
        """
        定义节点间连接边

        简单的串行处理：sentiment -> chat

        参数:
            graph: 要定义边的状态图
        """
        # 直接连接：sentiment分析 -> 聊天回复
        graph.add_edge(AgentNodes.SENTIMENT_NODE, AgentNodes.SALES_NODE)

        logger.debug("工作流边定义完成 - sentiment -> chat")

    def _set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点

        参数:
            graph: 要设置入口出口的状态图
        """
        # 设置工作流入口点 - 从情感分析开始
        graph.set_entry_point(AgentNodes.SENTIMENT_NODE)

        # 设置工作流出口点 - 聊天节点是流程的结束
        graph.set_finish_point(AgentNodes.SALES_NODE)

        logger.debug("工作流入口出口点设置完成")

    async def _process_agent_node(self, state: dict, node_name: str) -> dict:
        """
        通用智能体节点处理方法

        参数:
            state: 当前对话状态（dict类型）
            node_name: 节点名称

        返回:
            dict: 更新后的状态字典
        """
        agent = self.agents.get(node_name)
        if not agent:
            logger.error(f"智能体未找到: {node_name}")
            raise ValueError(f"Agent '{node_name}' not found")

        try:
            # 修复：直接使用dict状态，无需model_dump转换
            # 确保 input 兼容映射为各 Agent 期望的 customer_input
            state.setdefault("customer_input", state.get("input"))

            # 调试日志：记录节点处理前的状态
            logger.debug(f"节点 {node_name} 处理前状态键: {list(state.keys())}")
            if "sales_prompt" in state:
                logger.debug(f"节点 {node_name} 接收到sales_prompt，长度: {len(state['sales_prompt'])}")

            result_state = await agent.process_conversation(state)

            # 调试日志：记录节点处理后的状态
            logger.debug(f"节点 {node_name} 处理后状态键: {list(result_state.keys())}")
            if "sales_prompt" in result_state:
                logger.debug(f"节点 {node_name} 输出sales_prompt，长度: {len(result_state['sales_prompt'])}")

            logger.debug(f"节点处理完成: {node_name}")
            return result_state

        except Exception as e:
            logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            raise e

    def _create_agent_node(self, node_name: str):
        """创建智能体节点的通用方法"""
        async def agent_node(state: dict) -> dict:
            return await self._process_agent_node(state, node_name)
        return agent_node
