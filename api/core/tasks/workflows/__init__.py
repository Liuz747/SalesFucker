"""
Temporal工作流模块初始化

该模块包含所有Temporal工作流定义，用于处理各种定时消息任务。
"""

from .greeting_workflow import GreetingWorkflow
from .conversation_preservation_workflow import ConversationPreservationWorkflow
from .thread_awakening_workflow import ThreadAwakeningWorkflow

def get_all_workflows() -> list[type]:
    """获取所有注册的工作流类"""
    return [
        GreetingWorkflow,
        ConversationPreservationWorkflow,
        ThreadAwakeningWorkflow
    ]


__all__ = [
    "get_all_workflows",
    "GreetingWorkflow",
    "ConversationPreservationWorkflow",
    "ThreadAwakeningWorkflow"
]