"""
数字员工聊天工作流

实现聊天对话的具体工作流逻辑，包括节点处理、条件路由和状态管理。
"""

from typing import Optional, TYPE_CHECKING
from collections.abc import Callable

from langgraph.graph import StateGraph

from core.agents.base import BaseAgent
from core.entities import WorkflowExecutionModel
from utils import get_component_logger
from libs.constants import AgentNodes
from .base_workflow import BaseWorkflow

if TYPE_CHECKING:
    from core.agents.base import BaseAgent


logger = get_component_logger(__name__)

class ChatWorkflow(BaseWorkflow):
    """
    聊天工作流

    实现具体的聊天对话流程，包括合规检查、情感分析、
    意图识别、销售处理和记忆更新。

    包含增强的节点处理能力：
    - 智能体节点处理与错误恢复
    - 降级处理策略
    - 并行处理优化
    """
    
    def __init__(self, agents: dict[str, "BaseAgent"]):
        """
        初始化聊天工作流
        """
        self.agents = agents
        # self.fallback_handlers = self._init_fallback_handlers()
    
    def _register_nodes(self, graph: StateGraph):
        """
        注册工作流节点

        将所有智能体处理函数注册到工作流图中。

        参数:
            graph: 要注册节点的状态图
        """
        # 节点映射：节点名称 -> 智能体ID常量
        node_mappings = [
            WorkflowConstants.SENTIMENT_NODE,
            WorkflowConstants.SALES_NODE,
            WorkflowConstants.MEMORY_NODE,
        ]

        # 注册所有节点处理函数
        for node_name in node_mappings:
            graph.add_node(node_name, self._create_agent_node(node_name))

        logger.debug(f"已注册 {len(node_mappings)} 个工作流节点")
    
    def _define_edges(self, graph: StateGraph):
        """
        定义优化的节点间连接边

        实现简化的串行处理流程。

        参数:
            graph: 要定义边的状态图
        """
        # 简化的串行处理流程
        graph.add_edge(WorkflowConstants.SENTIMENT_NODE, WorkflowConstants.SALES_NODE)
        graph.add_edge(WorkflowConstants.SALES_NODE, WorkflowConstants.MEMORY_NODE)

        logger.debug("简化工作流边定义完成 - 移除合规检查节点")
    
    def _set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点
        
        参数:
            graph: 要设置入口出口的状态图
        """
        # 设置工作流入口点 - 从情感分析开始
        graph.set_entry_point(WorkflowConstants.SENTIMENT_NODE)

        # 设置工作流出口点 - 内存节点是正常流程的结束
        graph.set_finish_point(WorkflowConstants.MEMORY_NODE)
        
        logger.debug("工作流入口出口点设置完成")
    
    # def _init_fallback_handlers(self) -> dict[str, Callable]:
    #     """
    #     初始化降级处理器映射
        
    #     为每个节点类型定义特定的降级处理逻辑。
        
    #     返回:
    #         dict[str, Callable]: 节点名称到降级处理器的映射
    #     """
    #     return {
    #         WorkflowConstants.SENTIMENT_NODE: self._sentiment_fallback,
    #         WorkflowConstants.SALES_NODE: self._sales_fallback,
    #         WorkflowConstants.MEMORY_NODE: self._memory_fallback,
    #     }
    
    async def _process_agent_node(self, state: WorkflowExecutionModel, node_name: str) -> dict:
        """
        通用智能体节点处理方法

        统一处理智能体调用、错误处理和降级策略。

        参数:
            state: 当前对话状态字典
            node_name: 节点名称

        返回:
            dict: 更新后的状态字典
        """
        agent = self.agents.get(node_name)
        if not agent:
            logger.error(f"智能体未找到: {node_name}")
            raise ValueError(f"Agent '{node_name}' not found")

        try:
            # 将 Pydantic 模型转换为 dict 供 agent 处理
            state_dict = state.model_dump()
            # 将 input 兼容映射为各 Agent 期望的 customer_input
            state_dict.setdefault("customer_input", state.input)

            result_state = await agent.process_conversation(state_dict)

            # 将agent处理结果合并回原始状态
            if isinstance(result_state, dict):
                # 特殊处理：如果agent返回了values字段，直接使用
                if "values" in result_state and result_state["values"] is not None:
                    state.values = result_state["values"]
                elif "agent_responses" in result_state:
                    # 获取现有的 agent_responses
                    existing_values = state.values or {}
                    existing_agent_responses = existing_values.get("agent_responses", {})
                    new_responses = result_state["agent_responses"]

                    # 合并 agent_responses，新的不覆盖现有的
                    existing_agent_responses.update(new_responses)

                    # 更新 values 中的 agent_responses
                    if state.values is None:
                        state.values = {}
                    state.values["agent_responses"] = existing_agent_responses

                # 更新其他字段到状态模型
                for key, value in result_state.items():
                    if hasattr(state, key) and key not in ["values", "agent_responses"]:
                        setattr(state, key, value)

            return state

        except Exception as e:
            logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            raise e

    def _create_agent_node(self, node_name: str):
        """创建智能体节点的通用方法"""
        async def agent_node(state: WorkflowExecutionModel) -> dict:
            return await self._process_agent_node(state, node_name)
        return agent_node
    
    # ============ 降级处理器 ============
    def _sentiment_fallback(self, state: WorkflowExecutionModel, error: Optional[Exception]) -> dict:
        """情感与意图综合分析降级处理"""
        return {
            "sentiment_analysis": {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            },
            "intent_analysis": {
                "intent": "general_inquiry",
                "confidence": 0.5,
                "category": "unknown",
                "fallback": True
            }
        }

    # def _sales_fallback(self, state: WorkflowExecutionModel, error: Optional[Exception]) -> dict:
    #     """销售智能体降级处理"""
    #     agent_responses = state.agent_responses.copy()
    #     agent_responses["sales_agent"] = {
    #         "response": "感谢您的咨询！我很乐意为您推荐合适的美容产品。请告诉我您具体的需求？",
    #         "fallback": True,
    #         "timestamp": state.timestamp
    #     }
    #     return {"agent_responses": agent_responses}

    # def _memory_fallback(self, state: WorkflowExecutionModel, error: Optional[Exception]) -> dict:
    #     """记忆管理降级处理"""
    #     return {
    #         "memory_update": {
    #             "status": StatusConstants.FAILED,
    #             "message": "记忆系统暂时不可用",
    #             "fallback": True
    #         }
    #     }
