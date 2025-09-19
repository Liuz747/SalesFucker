"""
智能体编排管理模块

该模块负责使用LangGraph管理多智能体的工作流编排。

核心功能:
- 多智能体编排协调
- 主要处理接口管理
- 模块间协调和错误处理
- 多租户工作流隔离
"""

from typing import Any

from models import WorkflowRun, WorkflowExecutionModel
from core.factories import create_agents_set
from .workflow_builder import WorkflowBuilder
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
        self.state_manager = StateManager()

        # 初始化智能体
        self.agents = self._initialize_agents()

        # 使用注入的智能体构建工作流图
        self.workflow_builder = WorkflowBuilder(self.agents)
        self.graph = self.workflow_builder.build_graph()
        
        self.logger.info("多智能体编排器初始化完成")
    
    def _initialize_agents(self):
        """
        初始化智能体集合
        
        创建并注册所有必要的智能体。
        """
        
        try:
            # 创建智能体集合
            agents = create_agents_set()
            
            self.logger.info(f"智能体初始化完成，成功创建 {len(agents)} 个智能体")
            
            # 记录创建的智能体
            for agent_type, agent in agents.items():
                self.logger.debug(f"已创建智能体: {agent_type} -> {agent.agent_id}")
                
            return agents
        except Exception as e:
            self.logger.error(f"智能体初始化失败: {e}", exc_info=True)
            return {}
    
    async def process_conversation(self, workflow: WorkflowRun) -> WorkflowExecutionModel:
        """
        处理客户对话的主入口函数
        
        通过LangGraph工作流协调所有智能体处理客户输入，
        返回完整的对话处理结果。
        
        参数:
            workflow: 工作流运行
            
        返回:
            WorkflowRun: 处理完成的工作流运行
        """
        self.logger.info(
            f"开始处理对话 - 租户: {workflow.tenant_id}, "
            f"助手: {workflow.assistant_id}, 输入类型: {workflow.type}"
        )
        start_time = get_current_datetime()
        try:
            # 构建初始工作流状态
            initial_state = self.state_manager.create_initial_state(workflow)

            # 执行工作流
            result_dict = await self.graph.ainvoke(initial_state)
            processing_time = get_processing_time_ms(start_time)

            self.logger.info(
                f"对话处理完成 - 耗时: {processing_time:.2f}ms, "
                f"状态: {'成功' if result_dict.get('processing_complete') else '失败'}"
            )
            
            # Simple Langfuse tracing - just log the conversation
            trace_conversation(
                input_data={
                    "customer_input": workflow.input,
                    "input_type": workflow.type,
                    "tenant_id": workflow.tenant_id
                },
                output_data={
                    "final_response": result_dict.get("final_response"),
                    "agents_executed": list(result_dict.get("agent_responses", {}).keys()),
                    "processing_complete": result_dict.get("processing_complete", False)
                },
                metadata={
                    "tenant_id": workflow.tenant_id,
                    "workflow_type": "multi_agent_conversation"
                }
            )

            # 构建执行结果模型（元数据 + 会话结果）
            execution = WorkflowExecutionModel(
                execution_id=workflow.run_id,
                thread_id=workflow.thread_id,
                assistant_id=workflow.assistant_id,
                tenant_id=workflow.tenant_id,
                input_content=workflow.input,
                input_type=workflow.type,
                created_at=start_time,
                final_response=result_dict.get("final_response", ""),
                processing_complete=result_dict.get("processing_complete", False),
                agent_responses=result_dict.get("agent_responses", {}),
            )
            return execution
            
        except Exception as e:
            self.logger.error(f"对话处理失败: {e}", exc_info=True)
            # 返回统一错误状态
            # 统一错误时返回执行模型
            return WorkflowExecutionModel(
                execution_id=workflow.run_id,
                thread_id=workflow.thread_id,
                assistant_id=workflow.assistant_id,
                tenant_id=workflow.tenant_id,
                input_content=workflow.input,
                input_type=workflow.type,
                created_at=start_time,
                final_response="系统暂时不可用，请稍后重试。",
                processing_complete=True,
                agent_responses={},
            )
    
    def get_workflow_status(self) -> dict[str, Any]:
        """
        获取工作流状态信息
        
        返回:
            Dict[str, Any]: 工作流状态和统计信息
        """
        return {
            "graph_compiled": self.graph is not None,
        }
    
