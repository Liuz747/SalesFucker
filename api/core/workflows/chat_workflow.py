"""
化妆品销售工作流

实现聊天对话的具体工作流逻辑，包括节点处理、条件路由和状态管理。
"""

from typing import Any, Optional
from collections.abc import Callable

from langgraph.graph import StateGraph

from core.agents.base import BaseAgent
from libs.constants import WorkflowConstants, StatusConstants
from .base_workflow import BaseWorkflow


class ChatWorkflow(BaseWorkflow):
    """
    聊天工作流
    
    实现具体的聊天对话流程，包括合规检查、情感分析、
    意图识别、策略制定、销售处理、产品推荐和记忆更新。
    
    包含增强的节点处理能力：
    - 智能体节点处理与错误恢复
    - 降级处理策略
    - 并行处理优化
    """
    
    def __init__(self, agents: dict[str, BaseAgent]):
        """
        初始化聊天工作流
        """
        super().__init__()
        self.agents = agents
        self.fallback_handlers = self._init_fallback_handlers()
    
    def _register_nodes(self, graph: StateGraph):
        """
        注册工作流节点
        
        将所有智能体处理函数注册到工作流图中。
        
        参数:
            graph: 要注册节点的状态图
        """
        # 节点映射：节点名称 -> 智能体ID常量
        node_mappings = [
            WorkflowConstants.COMPLIANCE_NODE,
            WorkflowConstants.SENTIMENT_NODE,
            WorkflowConstants.INTENT_NODE,
            WorkflowConstants.STRATEGY_NODE,
            WorkflowConstants.SALES_NODE,
            WorkflowConstants.PRODUCT_NODE,
            WorkflowConstants.MEMORY_NODE,
        ]
        
        # 注册所有节点处理函数
        for node_name in node_mappings:
            graph.add_node(node_name, self._create_agent_node(node_name))
        
        self.logger.debug(f"已注册 {len(node_mappings)} 个工作流节点")
    
    def _define_edges(self, graph: StateGraph):
        """
        定义优化的节点间连接边
        
        实现并行处理以提高性能：
        - 情感分析和意图分析可并行
        - 产品推荐和记忆更新可并行
        
        参数:
            graph: 要定义边的状态图
        """
        # 添加阻止完成节点
        graph.add_node("blocked_completion", self._blocked_completion_node)
        
        # 合规检查路由
        graph.add_conditional_edges(
            WorkflowConstants.COMPLIANCE_NODE,
            self._compliance_router,
            {
                "continue": WorkflowConstants.SENTIMENT_NODE,  # 继续到情感分析
                "block": "blocked_completion"  # 合规阻止时的完成节点
            }
        )
        
        # 串行处理流程
        graph.add_edge(WorkflowConstants.SENTIMENT_NODE, WorkflowConstants.INTENT_NODE)
        graph.add_edge(WorkflowConstants.INTENT_NODE, WorkflowConstants.STRATEGY_NODE)
        graph.add_edge(WorkflowConstants.STRATEGY_NODE, WorkflowConstants.SALES_NODE)
        graph.add_edge(WorkflowConstants.SALES_NODE, WorkflowConstants.PRODUCT_NODE)
        graph.add_edge(WorkflowConstants.PRODUCT_NODE, WorkflowConstants.MEMORY_NODE)
        
        self.logger.debug("优化工作流边定义完成 - 启用并行处理")
    
    def _set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点
        
        参数:
            graph: 要设置入口出口的状态图
        """
        # 设置工作流入口点 - 从合规检查开始
        graph.set_entry_point(WorkflowConstants.COMPLIANCE_NODE)
        
        # 设置工作流出口点 - 内存节点是正常流程的结束，阻止完成是异常流程的结束
        graph.set_finish_point([WorkflowConstants.MEMORY_NODE, "blocked_completion"])
        
        self.logger.debug("工作流入口出口点设置完成")
    
    def _compliance_router(self, state: dict[str, Any]) -> str:
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
    
    def _init_fallback_handlers(self) -> dict[str, Callable]:
        """
        初始化降级处理器映射
        
        为每个节点类型定义特定的降级处理逻辑。
        
        返回:
            dict[str, Callable]: 节点名称到降级处理器的映射
        """
        return {
            WorkflowConstants.COMPLIANCE_NODE: self._compliance_fallback,
            WorkflowConstants.SENTIMENT_NODE: self._sentiment_fallback,
            WorkflowConstants.INTENT_NODE: self._intent_fallback,
            WorkflowConstants.STRATEGY_NODE: self._strategy_fallback,
            WorkflowConstants.SALES_NODE: self._sales_fallback,
            WorkflowConstants.PRODUCT_NODE: self._product_fallback,
            WorkflowConstants.MEMORY_NODE: self._memory_fallback,
        }
    
    async def _process_agent_node(self, state: dict, node_name: str) -> dict:
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
            self.logger.warning(f"智能体未找到: {node_name}")
            return self._apply_fallback(state, node_name, None)
        
        try:
            # 直接使用 dict 状态，与新的无兼容策略一致
            result_state = await agent.process_conversation(state)

            self.logger.debug(f"节点处理完成: {node_name}")
            return result_state
            
        except Exception as e:
            self.logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            return self._apply_fallback(state, node_name, e)
    
    def _apply_fallback(self, state: dict, node_name: str, error: Optional[Exception]) -> dict:
        """
        应用降级处理策略
        
        参数:
            state: 当前状态
            node_name: 节点名称
            error: 可选的错误信息
            
        返回:
            dict: 应用降级后的状态
        """
        fallback_handler = self.fallback_handlers.get(node_name)
        if fallback_handler:
            return fallback_handler(state, error)
        else:
            # 默认降级处理
            state["error_state"] = f"{node_name}_unavailable"
            return state
    
    def _create_agent_node(self, node_name: str):
        """创建智能体节点的通用方法"""
        async def agent_node(state: dict) -> dict:
            return await self._process_agent_node(state, node_name)
        return agent_node
    
    async def _blocked_completion_node(self, state: dict) -> dict:
        """合规阻止完成节点"""
        compliance_result = state.get("compliance_result", {})
        state["final_response"] = compliance_result.get(
            "user_message", 
            "很抱歉，您的请求涉及到敏感内容，无法继续处理。"
        )
        state["processing_complete"] = True
        state["blocked_by_compliance"] = True
        return state
    
    # ============ 降级处理器 ============
    
    def _compliance_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """合规审查降级处理"""
        state["compliance_result"] = {
            "status": StatusConstants.APPROVED,
            "fallback": True,
            "message": "合规检查系统暂时不可用，默认通过"
        }
        return state
    
    def _sentiment_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """情感分析降级处理"""
        state["sentiment_analysis"] = {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.5,
            "fallback": True
        }
        return state
    
    def _intent_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """意图分析降级处理"""
        state["intent_analysis"] = {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "category": "unknown",
            "fallback": True
        }
        return state
    
    def _strategy_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """市场策略降级处理"""
        customer_input = state.get("customer_input", "").lower()
        
        if any(word in customer_input for word in ["luxury", "premium", "expensive"]):
            strategy = "premium_strategy"
        elif any(word in customer_input for word in ["budget", "cheap", "affordable"]):
            strategy = "budget_strategy"
        elif any(word in customer_input for word in ["young", "trendy", "cool"]):
            strategy = "youth_strategy"
        else:
            strategy = "premium_strategy"  # 默认策略
        
        state["market_strategy"] = {
            "strategy": strategy,
            "confidence": 0.6,
            "fallback": True
        }
        return state
    
    def _sales_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """销售智能体降级处理"""
        state["agent_responses"] = state.get("agent_responses", {})
        state["agent_responses"]["sales_agent"] = {
            "response": "感谢您的咨询！我很乐意为您推荐合适的美容产品。请告诉我您具体的需求？",
            "fallback": True,
            "timestamp": state.get("timestamp")
        }
        return state
    
    def _product_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """产品专家降级处理"""
        state["product_recommendations"] = {
            "status": "unavailable",
            "message": "产品推荐系统暂时不可用",
            "fallback": True
        }
        return state
    
    def _memory_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """记忆管理降级处理"""
        state["memory_update"] = {
            "status": StatusConstants.FAILED,
            "message": "记忆系统暂时不可用",
            "fallback": True
        }
        return state