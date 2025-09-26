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
        将工作流信息映射为 LangGraph 初始状态模型。
        """
        return WorkflowExecutionModel(
            workflow_id=workflow.workflow_id,
            thread_id=workflow.thread_id,
            assistant_id=workflow.assistant_id,
            tenant_id=workflow.tenant_id,
            input=workflow.input,
            started_at=workflow.created_at,
            exception_count=0,
            total_tokens=0
        )
    
    def create_error_state(
        self,
        state: WorkflowExecutionModel,
        message: str = "系统暂时不可用，请稍后重试。",
    ) -> WorkflowExecutionModel:
        """
        构建统一的错误状态模型。
        """
        return WorkflowExecutionModel(
            workflow_id=state.workflow_id,
            thread_id=state.thread_id,
            assistant_id=state.assistant_id,
            tenant_id=state.tenant_id,
            input=state.input,
            started_at=state.started_at,
            finished_at=state.finished_at,
            exception_count=state.exception_count + 1,
            error_message=message
        )
    