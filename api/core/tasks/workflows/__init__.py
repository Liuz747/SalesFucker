"""
Temporal工作流模块初始化

该模块包含所有Temporal工作流定义，用于处理各种定时消息任务。
"""

from .conversation_preservation_workflow import ConversationPreservationWorkflow
from .thread_awakening_workflow import ThreadAwakeningWorkflow

def get_all_workflows() -> list[type]:
    """获取所有注册的工作流类"""
    return [
        ConversationPreservationWorkflow,
        ThreadAwakeningWorkflow
    ]


__all__ = [
    "get_all_workflows",
    "ConversationPreservationWorkflow",
    "ThreadAwakeningWorkflow"
]