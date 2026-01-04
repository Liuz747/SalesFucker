from langgraph.graph import StateGraph

from core.agents import BaseAgent
from core.entities import WorkflowExecutionModel
from libs.types import AgentNodeType
from .base_workflow import BaseWorkflow


class TestWorkflow(BaseWorkflow):
    """最小单Agent节点测试工作流"""
    
    def __init__(self, agents: dict[AgentNodeType, BaseAgent]):
        """初始化测试工作流"""
        super().__init__(agents)
    
    def register_nodes(self, graph: StateGraph):
        """注册单个Agent节点用于独立测试"""
        graph.add_node("single_node", self._single_node)

    def define_edges(self, graph: StateGraph):
        pass
    
    def set_entry_exit_points(self, graph: StateGraph):
        """设置入口和出口为同一单节点"""
        graph.set_entry_point("single_node")
        graph.set_finish_point("single_node")

    async def _single_node(self, state: WorkflowExecutionModel) -> dict:
        """按 target_node 运行对应Agent并直接返回结果"""
        target_node = AgentNodeType.CHAT
        agent = self.agents.get(target_node)
        if not agent:
            raise ValueError(f"Agent '{target_node}' 未找到")
        return await agent.process_conversation(state)
