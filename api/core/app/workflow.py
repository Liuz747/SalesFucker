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

from typing import Any

from langgraph.graph import StateGraph

from utils import get_component_logger
from core.workflows import ChatWorkflow


class WorkflowBuilder:
    """
    工作流构建器
    
    负责构建LangGraph工作流图，使用具体工作流实现来定义
    智能体节点间的连接关系和条件路由逻辑。
    
    属性:
        logger: 日志记录器
        workflow: 具体工作流实现
    """
    
    def __init__(self):
        """
        初始化工作流构建器
        """
        self.logger = get_component_logger(__name__)
        self.workflow = ChatWorkflow()
    
    def build_graph(self) -> StateGraph:
        """
        构建LangGraph工作流图
        
        创建包含所有智能体节点和路由逻辑的状态图。
        定义标准的聊天对话流程。
        
        返回:
            StateGraph: 配置完成的LangGraph状态图
        """
        # 创建状态图，使用字典作为状态类型
        graph = StateGraph(dict)
        
        # 注册节点处理函数
        self.workflow._register_nodes(graph)
        
        # 定义节点间的连接关系
        self.workflow._define_edges(graph)
        
        # 设置入口和出口点
        self.workflow._set_entry_exit_points(graph)
        
        # 编译工作流图
        compiled_graph = graph.compile()
        
        self.logger.info("工作流图构建完成")
        return compiled_graph
    
    def get_workflow_info(self) -> dict[str, Any]:
        """
        获取工作流配置信息
        
        返回:
            dict[str, Any]: 工作流配置信息
        """
        return {
            "node_count": 7,
            "nodes": ["compliance_review", "sentiment_analysis", "intent_analysis", "strategy", "sales", "product_expert", "memory"],
            "entry_point": "compliance_review",
            "exit_point": "memory",
            "conditional_routers": ["compliance_router"],
            "workflow_type": "ChatWorkflow",
            "component": "WorkflowBuilder"
        }
    
    def get_performance_metrics(self) -> dict[str, Any]:
        """
        获取工作流性能指标
        
        返回:
            dict[str, Any]: 性能相关指标
        """
        return {
            "parallel_processing_enabled": True,
            "max_concurrent_agents": 3,
            "performance_optimizations": [
                "parallel_sentiment_intent_analysis",
                "parallel_product_memory_processing",
                "async_agent_execution",
                "conditional_routing_optimization"
            ]
        }