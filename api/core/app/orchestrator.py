"""
智能体编排管理模块

该模块负责使用LangGraph管理多智能体的工作流编排。

核心功能:
- 多智能体编排协调
- 主要处理接口管理
- 模块间协调和错误处理
- 多租户工作流隔离
"""

from langfuse import observe, get_client

from models import WorkflowRun
from ..workflows import ChatWorkflow, TestWorkflow
from .entities import WorkflowExecutionModel
from .workflow_builder import WorkflowBuilder
from .state_manager import StateManager
from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time_ms,
    flush_traces
)

logger = get_component_logger(__name__)


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
    """
    
    def __init__(self):
        # 初始化模块化组件
        self.state_manager = StateManager()

        # 构建工作流图
        self.workflow_builder = WorkflowBuilder(TestWorkflow)
        self.graph = self.workflow_builder.build_graph()
        
        logger.info("多智能体编排器初始化完成")
    
    @observe(name="multi-agent-conversation", as_type="span")
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
        logger.info(
            f"开始处理对话 - 租户: {workflow.tenant_id}, "
            f"助手: {workflow.assistant_id}, 输入类型: {workflow.type}"
        )
        start_time = get_current_datetime()
        try:
            # 构建初始工作流状态
            initial_state = self.state_manager.create_initial_state(workflow)

            # 执行工作流
            result_dict = await self.graph.ainvoke(initial_state.model_dump())
            processing_time = get_processing_time_ms(start_time)

            logger.info(
                f"对话处理完成 - 耗时: {processing_time:.2f}ms, "
                f"状态: {'成功' if result_dict.get('processing_complete') else '失败'}"
            )
            
            # 更新Langfuse追踪信息
            langfuse_trace = get_client()
            langfuse_trace.update_current_trace(
                name=f"conversation-{workflow.workflow_id}",
                user_id=workflow.tenant_id,
                input={
                    "customer_input": workflow.input,
                    "input_type": workflow.type,
                    "tenant_id": workflow.tenant_id
                },
                output={
                    "final_response": result_dict.get("final_response"),
                    "agents_executed": list(result_dict.get("agent_responses", {}).keys()),
                    "processing_complete": result_dict.get("processing_complete", False)
                },
                metadata={
                    "tenant_id": workflow.tenant_id,
                    "workflow_type": "multi_agent_conversation",
                    "processing_time_ms": processing_time
                },
                tags=["multi-agent", "conversation", workflow.type]
            )

            # 强制发送追踪数据到Langfuse
            flush_traces()

            # 构建执行结果模型（元数据 + 会话结果）
            return WorkflowExecutionModel(
                workflow_id=workflow.workflow_id,
                thread_id=workflow.thread_id,
                assistant_id=workflow.assistant_id,
                tenant_id=workflow.tenant_id,
                input=workflow.input,
                type=workflow.type,
                created_at=start_time,
                # 状态字段
                customer_input=result_dict.get("customer_input", workflow.input),
                input_type=result_dict.get("input_type", workflow.type),
                compliance_result=result_dict.get("compliance_result", {}),
                sentiment_analysis=result_dict.get("sentiment_analysis", {}),
                intent_analysis=result_dict.get("intent_analysis", {}),
                market_strategy=result_dict.get("market_strategy", {}),
                product_recommendations=result_dict.get("product_recommendations", {}),
                memory_update=result_dict.get("memory_update", {}),
                agent_responses=result_dict.get("agent_responses", {}),
                final_response=result_dict.get("final_response", ""),
                processing_complete=result_dict.get("processing_complete", False),
                error_state=result_dict.get("error_state"),
                blocked_by_compliance=result_dict.get("blocked_by_compliance", False),
            )
            
        except Exception as e:
            logger.error(f"对话处理失败: {e}", exc_info=True)
            # 返回统一错误状态
            return WorkflowExecutionModel(
                workflow_id=workflow.workflow_id,
                thread_id=workflow.thread_id,
                assistant_id=workflow.assistant_id,
                tenant_id=workflow.tenant_id,
                input=workflow.input,
                type=workflow.type,
                created_at=start_time,
                customer_input=workflow.input,
                input_type=workflow.type,
                final_response="系统暂时不可用，请稍后重试。",
                processing_complete=True,
                error_state="orchestrator_failed",
                agent_responses={},
            )
    
