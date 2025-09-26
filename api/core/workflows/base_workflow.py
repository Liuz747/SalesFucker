"""
基础工作流类

定义工作流的抽象接口和通用功能。
"""

from abc import ABC, abstractmethod

from langgraph.graph import StateGraph


class BaseWorkflow(ABC):
    """
    工作流基类
    
    定义工作流的抽象接口和通用功能。
    所有具体工作流实现都应该继承此基类。
    """
    
    def __init__(self):
        """初始化基础工作流"""
        pass
    
    @abstractmethod
    def _register_nodes(self, graph: StateGraph):
        """
        注册工作流节点
        
        参数:
            graph: 要注册节点的状态图
        """
        pass
    
    @abstractmethod
    def _define_edges(self, graph: StateGraph):
        """
        定义节点间连接边
        
        参数:
            graph: 要定义边的状态图
        """
        pass
    
    @abstractmethod
    def _set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点
        
        参数:
            graph: 要设置入口出口的状态图
        """
        pass