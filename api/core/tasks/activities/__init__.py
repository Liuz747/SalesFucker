"""
Temporal 活动注册

集中声明需要注册到 Temporal Worker 的活动函数。
"""

# from typing import Callable, List

from .callback_activities import send_callback_message
from .llm_activities import invoke_task_llm
from .monitoring_activities import check_thread_activity_status
# from .memory_activities import (
#     get_customer_memory_context,
#     update_customer_memory,
#     has_customer_messages,
#     get_thread_message_count,
#     get_last_assistant_message_time,
# )
# from .generation_activities import (
#     generate_personalized_message,
#     generate_ice_breaking_message,
#     generate_follow_up_message,
#     generate_holiday_message,
#     generate_marketing_message,
# )
# from .customer_activities import (
#     get_customer_last_interaction,
#     update_message_frequency_record,
#     get_eligible_customers,
# )

# def get_all_activities() -> List[Callable]:
#     """返回需要注册的活动列表。"""
#     return [
#         # 内存相关活动
#         get_customer_memory_context,
#         update_customer_memory,
#         has_customer_messages,
#         get_thread_message_count,
#         get_last_assistant_message_time,

#         # 消息生成活动
#         generate_personalized_message,
#         generate_ice_breaking_message,
#         generate_follow_up_message,
#         generate_holiday_message,
#         generate_marketing_message,

#         # 消息发送与校验活动
#         send_callback_message,

#         # LLM 活动
#         invoke_task_llm,

#         # 客户信息活动
#         get_customer_last_interaction,
#         update_message_frequency_record,
#         get_eligible_customers,

#         # 线程监控活动
#         check_thread_activity_status
#     ]


__all__ = [
    "send_callback_message",
    "invoke_task_llm",
    "check_thread_activity_status"
]
