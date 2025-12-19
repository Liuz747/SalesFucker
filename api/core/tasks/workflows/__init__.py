"""
Temporal工作流模块初始化

该模块包含所有Temporal工作流定义，用于处理各种定时消息任务。

工作流类型:
- ScheduledMessagingWorkflow: 主要消息调度工作流
- GreetingWorkflow: 开场白消息工作流
- FollowUpWorkflow: 跟进消息工作流
- HolidayBroadcastWorkflow: 节假日广播工作流
- MarketingCampaignWorkflow: 营销活动工作流
"""

from .greeting_workflow import GreetingWorkflow
from .conversation_preservation_workflow import ConversationPreservationWorkflow

# def get_all_workflows() -> List[Type]:
#     """获取所有注册的工作流类"""
#     return [
#         ScheduledMessagingWorkflow,
#         IceBreakingWorkflow,
#         FollowUpWorkflow,
#         HolidayBroadcastWorkflow,
#         MarketingCampaignWorkflow,
#     ]


__all__ = [
    "GreetingWorkflow",
    "ConversationPreservationWorkflow"
]