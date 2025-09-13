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

from core.agents.base import ThreadState
from .workflow import WorkflowBuilder
from .state_manager import StateManager
from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time_ms
)
from utils.tracer_client import trace_conversation


class Orchestrator:
    """
    多智能体编排器
    
    使用LangGraph框架协调多个智能体的工作流程。
    
    采用模块化设计：
    - WorkflowBuilder: 工作流构建和节点处理
    - StateManager: 状态管理和监控
    
    属性:
        graph: LangGraph工作流图实例
        workflow_builder: 工作流构建器
        state_manager: 状态管理器
        logger: 日志记录器
    """
    
    def __init__(self):
        """
        初始化多智能体编排器
        """
        self.logger = get_component_logger(__name__)
        
        # 初始化模块化组件
        self.workflow_builder = WorkflowBuilder()
        self.state_manager = StateManager()
        
        # 初始化智能体
        self._initialize_agents()
        
        # 构建工作流图
        self.graph = self.workflow_builder.build_graph()
        
        self.logger.info("多智能体编排器初始化完成")
    
    def _initialize_agents(self):
        """
        初始化智能体集合
        
        创建并注册所有必要的智能体。
        """
        from core.factories.agent_factory import create_agent_set
        
        try:
            # 创建并自动注册智能体集合
            agents = create_agent_set(auto_register=True)
            
            self.logger.info(f"智能体初始化完成，成功创建 {len(agents)} 个智能体")
            
            # 记录创建的智能体
            for agent_type, agent in agents.items():
                self.logger.debug(f"已创建智能体: {agent_type} -> {agent.agent_id}")
                
        except Exception as e:
            self.logger.error(f"智能体初始化失败: {e}", exc_info=True)
            # 不抛出异常，允许编排器继续运行（可能会有部分功能降级）
    
    async def process_conversation(
            self, 
            customer_input: str, 
            tenant_id: str,
            customer_id: Optional[str] = None,
            input_type: str = "text"
        ) -> Dict[str, Any]:
        """
        处理客户对话的主入口函数
        
        通过LangGraph工作流协调所有智能体处理客户输入，
        返回完整的对话处理结果。
        
        参数:
            customer_input: 客户输入内容
            tenant_id: 租户标识符
            customer_id: 可选的客户标识符
            input_type: 输入类型 (text/voice/image)
            
        返回:
            ThreadState: 处理完成的对话状态
        """
        # 创建初始对话状态
        initial_state = self.state_manager.create_initial_state(
            customer_input, customer_id, input_type, tenant_id
        )
        
        # 验证状态有效性
        if not self.state_manager.validate_state(initial_state):
            error_msg = "无效的对话状态"
            return self.state_manager.create_error_state(
                initial_state, Exception(error_msg)
            )
        
        self.logger.info(
            f"开始处理对话 - 租户: {tenant_id}, "
            f"客户: {customer_id}, 输入类型: {input_type}"
        )
        
        try:
            # 执行工作流处理
            result = await self._execute_workflow(initial_state)
            
            # Simple Langfuse tracing - just log the conversation
            trace_conversation(
                input_data={
                    "customer_input": customer_input,
                    "customer_id": customer_id,
                    "input_type": input_type,
                    "tenant_id": tenant_id
                },
                output_data={
                    "final_response": result.final_response,
                    "agents_executed": list(result.agent_responses.keys()),
                    "processing_complete": result.processing_complete
                },
                metadata={
                    "tenant_id": tenant_id,
                    "workflow_type": "multi_agent_conversation"
                }
            )
            
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
        
        返回:
            Dict[str, Any]: 工作流状态和统计信息
        """
        return {
            "graph_compiled": self.graph is not None,
            "state_statistics": self.state_manager.get_state_statistics()
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        返回:
            Dict[str, Any]: 系统健康状态信息
        """
        # 获取状态管理器健康状态
        state_health = self.state_manager.get_health_status()
        
        return {
            "status": "healthy" if self.graph is not None else "critical",
            "workflow_compiled": self.graph is not None,
            "state_manager_health": state_health
        }
    
    def reset_statistics(self):
        """
        重置所有统计信息
        """
        self.state_manager.reset_statistics()
        self.logger.info("编排器统计信息已重置")
    


# 全局编排器实例管理
_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """
    获取全局编排器实例
    
    返回:
        Orchestrator: 编排器实例
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    
    return _orchestrator_instance


def shutdown_orchestrator():
    """
    关闭编排器实例
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is not None:
        _orchestrator_instance.reset_statistics()
        _orchestrator_instance = None 