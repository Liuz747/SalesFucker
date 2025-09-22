"""
对话状态管理模块

该模块负责对话状态的管理、监控和状态转换。

核心功能:
- 对话状态初始化和验证
- 状态转换和更新管理
- 状态监控和统计
- 错误状态处理
"""

from models import WorkflowRun
from utils import get_component_logger
from .entities import WorkflowExecutionModel


logger = get_component_logger(__name__)


class StateManager:
    """
    对话状态管理器
    
    职责：
    - 将业务层输入映射为 LangGraph 初始状态
    - 规范工作流执行完成与错误时的状态结构
    - 提供最小但一致的状态字段集合
    """
    
    def __init__(self):
        pass
    
    def create_initial_state(self, workflow: WorkflowRun) -> WorkflowExecutionModel:
        """
        将工作流运行信息映射为 LangGraph 初始状态模型（最小必需字段）。
        """
        return WorkflowExecutionModel(
            workflow_id=workflow.workflow_id,
            thread_id=workflow.thread_id,
            assistant_id=workflow.assistant_id,
            tenant_id=workflow.tenant_id,
            input=workflow.input,
            type=workflow.type,
            # LangGraph 期望的初始状态字段
            customer_input=workflow.input,
            input_type=workflow.type,
        )
    
    def create_error_state(
        self,
        workflow: WorkflowRun,
        message: str = "系统暂时不可用，请稍后重试。",
        error_state: str = "orchestrator_failed",
    ) -> WorkflowExecutionModel:
        """
        构建统一的错误状态模型。
        """
        return WorkflowExecutionModel(
            workflow_id=workflow.workflow_id,
            thread_id=workflow.thread_id,
            assistant_id=workflow.assistant_id,
            tenant_id=workflow.tenant_id,
            input=workflow.input,
            type=workflow.type,
            customer_input=workflow.input,
            input_type=workflow.type,
            final_response=message,
            processing_complete=True,
            error_state=error_state,
            agent_responses={},
        )
    