"""
数字员工测试工作流

单节点测试：start -> node -> end。
通过 state["target_node"] 指定要运行的节点。
"""

from typing import Any

from langgraph.graph import StateGraph

from core.agents.base import BaseAgent
from .base_workflow import BaseWorkflow

class TestWorkflow(BaseWorkflow):
    """最小单节点测试工作流"""
    
    def __init__(self, agents: dict[str, BaseAgent]):
        """初始化测试工作流"""
        self.agents = agents
    
    def _register_nodes(self, graph: StateGraph):
        """注册单个代理节点用于独立测试"""
        graph.add_node("single_node", self._single_node)

    def _define_edges(self, graph: StateGraph):
        pass
    
    def _set_entry_exit_points(self, graph: StateGraph):
        """设置入口和出口为同一单节点"""
        graph.set_entry_point("single_node")
        graph.set_finish_point("single_node")

    async def _single_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """按 target_node 运行对应代理并直接返回结果"""
        target_node = "compliance_review"
        agent = self.agents[target_node]
        return await agent.process_conversation(state)