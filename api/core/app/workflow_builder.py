"""
工作流构建模块

该模块负责构建LangGraph工作流图，定义智能体节点和边的连接关系。
所有具体的智能体实现都应该继承此基类。

核心功能:
- LangGraph工作流图构建
- 节点处理器注册
- 条件路由定义
- 工作流状态管理
"""

from typing import Type

from langgraph.graph import StateGraph

from utils import get_component_logger
from core.entities import WorkflowExecutionModel
from ..workflows import BaseWorkflow
from ..factories import create_agents_set


logger = get_component_logger(__name__)


class WorkflowBuilder:
    """
    工作流构建器
    
    负责构建LangGraph工作流图，使用具体工作流实现来定义
    智能体节点间的连接关系和条件路由逻辑。
    
    属性:
        workflow: 具体工作流实现
    """
    
    def __init__(self, workflow: Type[BaseWorkflow]):
        """
        初始化工作流构建器
        
        参数: workflow: 工作流类
        """

        self.agents = create_agents_set()
        self.workflow = workflow(self.agents)
    
    def build_graph(self) -> StateGraph:
        """
        构建LangGraph工作流图
        
        创建包含所有智能体节点和路由逻辑的状态图。
        定义标准的聊天对话流程。
        
        返回:
            StateGraph: 配置完成的LangGraph状态图
        """
        # 创建状态图，使用字典作为状态类型
        graph = StateGraph(WorkflowExecutionModel)
        
        # 注册节点处理函数
        self.workflow._register_nodes(graph)
        
        # 定义节点间的连接关系
        self.workflow._define_edges(graph)
        
        # 设置入口和出口点
        self.workflow._set_entry_exit_points(graph)
        
        # 编译工作流图
        compiled_graph = graph.compile()
        
        logger.info("工作流图构建完成")
        return compiled_graph
    