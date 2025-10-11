"""
智能体编排管理模块

该模块负责使用LangGraph管理多智能体的工作流编排。

核心功能:
- 多智能体编排协调
- 主要处理接口管理
- 模块间协调和错误处理
- 多租户工作流隔离
- 多模态输入处理支持
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
    get_processing_time,
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
        支持文本和多模态输入（图像、音频）。

        参数:
            workflow: 工作流运行

        返回:
            WorkflowExecutionModel: 处理完成的工作流执行结果
        """
        logger.info(
            f"开始处理对话 - 租户: {workflow.tenant_id}, "
            f"助手: {workflow.assistant_id}"
        )
        start_time = get_current_datetime()

        try:
            # 构建初始工作流状态
            initial_state = self.state_manager.create_initial_state(workflow)

            # 执行工作流
            result = await self.graph.ainvoke(initial_state)
            elapsed_time = get_processing_time(start_time)

            logger.info(
                f"对话处理完成 - 耗时: {elapsed_time:.2f}s, "
                f"状态: {'成功' if not result.get('exception_count') else '失败'}"
            )

            # 更新Langfuse追踪信息
            langfuse_trace = get_client()
            # 检测是否为多模态输入
            is_multimodal = not isinstance(workflow.input, str)
            multimodal_count = len(workflow.input) if is_multimodal else 0

            langfuse_trace.update_current_trace(
                name=f"conversation-{workflow.workflow_id}",
                user_id=workflow.tenant_id,
                input={
                    "customer_input": workflow.input if isinstance(workflow.input, str) else f"[多模态内容: {multimodal_count}项]",
                    "tenant_id": workflow.tenant_id,
                    "is_multimodal": is_multimodal
                },
                output={
                    "final_response": result.get("final_response"),
                    "agents_executed": list(result.get("values", {}).keys()),
                    "processing_complete": result.get("processing_complete", False)
                },
                metadata={
                    "tenant_id": workflow.tenant_id,
                    "workflow_type": "multi_agent_conversation",
                    "processing_time": elapsed_time,
                    "multimodal_count": multimodal_count
                },
                tags=["multi-agent", "conversation"]
            )

            # 强制发送追踪数据到Langfuse
            flush_traces()

            # 构建执行结果模型（元数据 + 会话结果）
            return WorkflowExecutionModel(**result)

        except Exception as e:
            logger.error(f"对话处理失败: {e}", exc_info=True)
            # 返回统一错误状态
            raise
