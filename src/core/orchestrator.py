"""
智能体编排管理模块

该模块负责使用LangGraph管理多智能体的工作流编排。

核心功能:
- 多智能体编排协调
- 主要处理接口管理
- 模块间协调和错误处理
- 多租户工作流隔离
"""

from typing import Dict, Any, Optional

from src.agents.base import ThreadState
from .workflow import WorkflowBuilder
from .state_manager import ThreadStateManager
from libs.constants import StatusConstants
from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time_ms,
    StatusMixin,
    with_error_handling,
    ErrorHandler
)


class Orchestrator(StatusMixin):
    """
    多智能体编排器
    
    使用LangGraph框架协调多个智能体的工作流程。
    使用StatusMixin提供标准化状态管理功能。
    
    采用模块化设计：
    - WorkflowBuilder: 工作流构建和节点处理
    - ConversationStateManager: 状态管理和监控
    
    属性:
        tenant_id: 租户标识符，用于多租户隔离
        graph: LangGraph工作流图实例
        workflow_builder: 工作流构建器
        state_manager: 状态管理器
        node_mapping: 节点名称到智能体ID的映射
        logger: 日志记录器
        error_handler: 错误处理器
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化多智能体编排器
        
        参数:
            tenant_id: 租户标识符，确保智能体隔离
        """
        super().__init__()
        
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, tenant_id)
        self.error_handler = ErrorHandler(f"orchestrator_{tenant_id}")
        
        # 节点到智能体的映射关系
        self.node_mapping = {
            "compliance_review": f"compliance_review_{tenant_id}",
            "sentiment_analysis": f"sentiment_analysis_{tenant_id}",
            "intent_analysis": f"intent_analysis_{tenant_id}",
            "sales_agent": f"sales_agent_{tenant_id}",
            "product_expert": f"product_expert_{tenant_id}",
            "memory_agent": f"memory_agent_{tenant_id}",
            "market_strategy": f"market_strategy_{tenant_id}",
            "response_generator": f"response_generator_{tenant_id}"
        }
        
        # 初始化模块化组件
        self.workflow_builder = WorkflowBuilder(tenant_id, self.node_mapping)
        self.state_manager = ThreadStateManager(tenant_id)
        
        # 构建工作流图
        self.graph = self.workflow_builder.build_graph()
        
        self.logger.info(f"多智能体编排器初始化完成，租户: {tenant_id}")
    
    async def process_conversation(
            self, 
            customer_input: str, 
            customer_id: Optional[str] = None,
            input_type: str = "text"
        ) -> ThreadState:
        """
        处理客户对话的主入口函数
        
        通过LangGraph工作流协调所有智能体处理客户输入，
        返回完整的对话处理结果。
        
        参数:
            customer_input: 客户输入内容
            customer_id: 可选的客户标识符
            input_type: 输入类型 (text/voice/image)
            
        返回:
            ThreadState: 处理完成的对话状态
        """
        # 创建初始对话状态
        initial_state = self.state_manager.create_initial_state(
            customer_input, customer_id, input_type
        )
        
        # 验证状态有效性
        if not self.state_manager.validate_state(initial_state):
            error_msg = "无效的对话状态"
            return self.state_manager.create_error_state(
                initial_state, Exception(error_msg)
            )
        
        self.logger.info(
            f"开始处理对话 - 租户: {self.tenant_id}, "
            f"客户: {customer_id}, 输入类型: {input_type}"
        )
        
        try:
            # 执行工作流处理
            result = await self._execute_workflow(initial_state)
            return result
            
        except Exception as e:
            self.logger.error(f"对话处理失败: {e}", exc_info=True)
            return self.state_manager.create_error_state(initial_state, e)
    
    async def _execute_workflow(self, initial_state: ThreadState) -> ThreadState:
        """
        执行工作流处理
        
        参数:
            initial_state: 初始对话状态
            
        返回:
            ThreadState: 处理完成的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            # 将状态转换为字典格式供LangGraph使用
            state_dict = initial_state.model_dump()
            
            # 执行工作流
            result_dict = await self.graph.ainvoke(state_dict)
            processing_time = get_processing_time_ms(start_time)
            
            # 转换回线程状态对象
            result = ThreadState(**result_dict)
            
            # 更新统计信息
            self.state_manager.update_completion_stats(result, processing_time)
            
            self.logger.info(
                f"对话处理完成 - 耗时: {processing_time:.2f}ms, "
                f"状态: {'成功' if result.processing_complete else '失败'}"
            )
            
            return result
            
        except Exception as e:
            processing_time = get_processing_time_ms(start_time)
            self.logger.error(f"工作流执行失败，耗时: {processing_time:.2f}ms, 错误: {e}")
            raise
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        获取工作流状态信息
        
        使用StatusMixin提供标准化状态响应。
        
        返回:
            Dict[str, Any]: 工作流状态和统计信息
        """
        from src.agents.base import agent_registry
        
        available_agents = [
            agent_id for agent_id in self.node_mapping.values()
            if agent_registry.get_agent(agent_id) is not None
        ]
        
        status_data = {
            "tenant_id": self.tenant_id,
            "graph_compiled": self.graph is not None,
            "node_count": len(self.node_mapping),
            "node_mapping": self.node_mapping.copy(),
            "available_agents": available_agents,
            "unavailable_agents": [
                agent_id for agent_id in self.node_mapping.values()
                if agent_id not in available_agents
            ],
            "state_statistics": self.state_manager.get_state_statistics()
        }
        
        return self.create_status_response(status_data, "MultiAgentOrchestrator")
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        使用StatusMixin提供标准化健康响应。
        
        返回:
            Dict[str, Any]: 系统健康状态信息
        """
        from src.agents.base import agent_registry
        
        # 检查智能体可用性
        total_agents = len(self.node_mapping)
        available_agents = len([
            agent_id for agent_id in self.node_mapping.values()
            if agent_registry.get_agent(agent_id) is not None
        ])
        
        agent_availability = (available_agents / total_agents * 100) if total_agents > 0 else 0
        
        # 获取状态管理器健康状态
        state_health = self.state_manager.get_health_status()
        
        # 综合判断系统健康状态
        if agent_availability < 70 or state_health["status"] == StatusConstants.CRITICAL:
            overall_status = StatusConstants.CRITICAL
        elif agent_availability < 90 or state_health["status"] == StatusConstants.WARNING:
            overall_status = StatusConstants.WARNING
        else:
            overall_status = StatusConstants.HEALTHY
        
        metrics = {
            "agent_availability": agent_availability,
            "available_agents": available_agents,
            "total_agents": total_agents,
            "workflow_compiled": self.graph is not None
        }
        
        details = {
            "tenant_id": self.tenant_id,
            "state_manager_health": state_health
        }
        
        return self.create_metrics_response(metrics, details)
    
    def reset_statistics(self):
        """
        重置所有统计信息
        """
        self.state_manager.reset_statistics()
        self.logger.info("编排器统计信息已重置")
    
    def get_node_mapping(self) -> Dict[str, str]:
        """
        获取节点映射关系
        
        返回:
            Dict[str, str]: 节点到智能体的映射关系
        """
        return self.node_mapping.copy()


# 全局编排器实例管理
_orchestrator_instances: Dict[str, Orchestrator] = {}


def get_orchestrator(tenant_id: str) -> Orchestrator:
    """
    获取或创建租户编排器实例
    
    参数:
        tenant_id: 租户标识符
        
    返回:
        Orchestrator: 租户编排器实例
    """
    if tenant_id not in _orchestrator_instances:
        _orchestrator_instances[tenant_id] = Orchestrator(tenant_id)
    
    return _orchestrator_instances[tenant_id]


def shutdown_orchestrator(tenant_id: Optional[str] = None):
    """
    关闭编排器实例
    
    参数:
        tenant_id: 租户标识符，如果为None则关闭所有实例
    """
    global _orchestrator_instances
    
    if tenant_id is None:
        # 关闭所有实例
        for orchestrator in _orchestrator_instances.values():
            orchestrator.reset_statistics()
        _orchestrator_instances.clear()
    elif tenant_id in _orchestrator_instances:
        # 关闭特定租户实例
        _orchestrator_instances[tenant_id].reset_statistics()
        del _orchestrator_instances[tenant_id] 