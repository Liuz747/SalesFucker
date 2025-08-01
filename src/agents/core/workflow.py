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

from typing import Dict, Any
from langgraph.graph import StateGraph

from .node_processor import NodeProcessor
from src.utils import (
    get_component_logger,
    WorkflowConstants,
    StatusMixin
)


class WorkflowBuilder(StatusMixin):
    """
    工作流构建器
    
    负责构建LangGraph工作流图，使用StatusMixin提供标准化状态管理。
    定义智能体节点间的连接关系和条件路由逻辑。
    
    属性:
        tenant_id: 租户标识符
        node_mapping: 节点到智能体的映射关系
        node_processor: 节点处理器实例
        logger: 日志记录器
    """
    
    def __init__(self, tenant_id: str, node_mapping: Dict[str, str]):
        """
        初始化工作流构建器
        
        参数:
            tenant_id: 租户标识符
            node_mapping: 节点名称到智能体ID的映射
        """
        super().__init__()
        
        self.tenant_id = tenant_id
        self.node_mapping = node_mapping
        self.node_processor = NodeProcessor(tenant_id, node_mapping)
        self.logger = get_component_logger(__name__, tenant_id)
    
    def build_graph(self) -> StateGraph:
        """
        构建LangGraph工作流图
        
        创建包含所有智能体节点和路由逻辑的状态图。
        定义标准的化妆品销售对话流程。
        
        返回:
            StateGraph: 配置完成的LangGraph状态图
        """
        # 创建状态图，使用字典作为状态类型
        graph = StateGraph(dict)
        
        # 注册节点处理函数
        self._register_nodes(graph)
        
        # 定义节点间的连接关系
        self._define_edges(graph)
        
        # 设置入口和出口点
        self._set_entry_exit_points(graph)
        
        # 编译工作流图
        compiled_graph = graph.compile()
        
        self.logger.info(f"工作流图构建完成，租户: {self.tenant_id}")
        return compiled_graph
    
    def _register_nodes(self, graph: StateGraph):
        """
        注册工作流节点
        
        将所有智能体处理函数注册到工作流图中。
        
        参数:
            graph: 要注册节点的状态图
        """
        # 注册所有节点处理函数
        graph.add_node(WorkflowConstants.COMPLIANCE_NODE, self.node_processor.compliance_node)
        graph.add_node(WorkflowConstants.SENTIMENT_NODE, self.node_processor.sentiment_node)
        graph.add_node(WorkflowConstants.INTENT_NODE, self.node_processor.intent_node)
        graph.add_node(WorkflowConstants.STRATEGY_NODE, self.node_processor.strategy_node)
        graph.add_node(WorkflowConstants.SALES_NODE, self.node_processor.sales_node)
        graph.add_node(WorkflowConstants.PRODUCT_NODE, self.node_processor.product_node)
        graph.add_node(WorkflowConstants.MEMORY_NODE, self.node_processor.memory_node)
        graph.add_node(WorkflowConstants.RESPONSE_NODE, self.node_processor.response_node)
        
        self.logger.debug(f"已注册 {len(self.node_mapping)} 个工作流节点")
    
    def _define_edges(self, graph: StateGraph):
        """
        定义节点间的连接边
        
        建立智能体节点间的处理顺序和条件路由逻辑。
        
        参数:
            graph: 要定义边的状态图
        """
        # 标准处理流程：合规 -> 情感分析 -> 意图分析 -> 策略选择
        graph.add_edge(WorkflowConstants.COMPLIANCE_NODE, WorkflowConstants.SENTIMENT_NODE)
        graph.add_edge(WorkflowConstants.SENTIMENT_NODE, WorkflowConstants.INTENT_NODE)
        graph.add_edge(WorkflowConstants.INTENT_NODE, WorkflowConstants.STRATEGY_NODE)
        
        # 策略选择后分支处理
        graph.add_edge(WorkflowConstants.STRATEGY_NODE, WorkflowConstants.SALES_NODE)
        graph.add_edge(WorkflowConstants.SALES_NODE, WorkflowConstants.PRODUCT_NODE)
        
        # 记忆更新和响应生成
        graph.add_edge(WorkflowConstants.PRODUCT_NODE, WorkflowConstants.MEMORY_NODE)
        graph.add_edge(WorkflowConstants.MEMORY_NODE, WorkflowConstants.RESPONSE_NODE)
        
        # 添加条件路由 - 合规检查后的分支
        graph.add_conditional_edges(
            WorkflowConstants.COMPLIANCE_NODE,
            self._compliance_router,
            {
                "continue": WorkflowConstants.SENTIMENT_NODE,
                "block": WorkflowConstants.RESPONSE_NODE
            }
        )
        
        self.logger.debug("工作流边定义完成")
    
    def _set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点
        
        参数:
            graph: 要设置入口出口的状态图
        """
        # 设置工作流入口点 - 从合规检查开始
        graph.set_entry_point(WorkflowConstants.COMPLIANCE_NODE)
        
        # 设置工作流出口点 - 响应生成结束
        graph.set_finish_point(WorkflowConstants.RESPONSE_NODE)
        
        self.logger.debug("工作流入口出口点设置完成")
    
    def _compliance_router(self, state: Dict[str, Any]) -> str:
        """
        合规检查路由器
        
        根据合规检查结果决定后续处理路径。
        
        参数:
            state: 当前对话状态
            
        返回:
            str: 路由决策结果 ("continue" 或 "block")
        """
        compliance_result = state.get("compliance_result", {})
        
        # 检查合规状态
        compliance_status = compliance_result.get("status", "approved")
        
        if compliance_status == "blocked":
            self.logger.warning(f"内容被合规系统阻止: {state.get('customer_input', '')[:50]}...")
            return "block"
        
        return "continue"
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        获取工作流配置信息
        
        使用StatusMixin提供标准化状态响应。
        
        返回:
            Dict[str, Any]: 工作流配置信息
        """
        status_data = {
            "tenant_id": self.tenant_id,
            "node_count": len(self.node_mapping),
            "nodes": list(self.node_mapping.keys()),
            "node_mapping": self.node_mapping.copy(),
            "entry_point": WorkflowConstants.COMPLIANCE_NODE,
            "exit_point": WorkflowConstants.RESPONSE_NODE,
            "conditional_routers": ["compliance_router"]
        }
        
        return self.create_status_response(status_data, "WorkflowBuilder") 