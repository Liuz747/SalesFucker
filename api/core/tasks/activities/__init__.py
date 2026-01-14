"""
Temporal 活动注册

集中声明需要注册到 Temporal Worker 的活动函数。
"""

from collections.abc import Callable

from .awakening_activities import (
    scan_inactive_threads,
    prepare_awakening_context,
    update_awakened_thread
)
from .callback_activities import send_callback_message
from .generate_message_activity import invoke_task_llm
from .monitoring_activities import check_thread_activity_status
from .preservation_activities import (
    check_preservation_needed,
    evaluate_conversation_quality,
    preserve_conversation_to_elasticsearch
)


def get_all_activities() -> list[Callable]:
    """返回需要注册的活动列表。"""
    return [
        # 开场白工作流
        check_thread_activity_status,

        # 记忆存档工作流
        check_preservation_needed,
        evaluate_conversation_quality,
        preserve_conversation_to_elasticsearch,

        # 唤醒活动
        scan_inactive_threads,
        prepare_awakening_context,
        update_awakened_thread,

        # LLM 活动
        invoke_task_llm,

        # 消息发送与校验活动
        send_callback_message
    ]


__all__ = [
    "get_all_activities",
    "send_callback_message",
    "invoke_task_llm",
    "check_thread_activity_status",
    "check_preservation_needed",
    "evaluate_conversation_quality",
    "preserve_conversation_to_elasticsearch",
    "scan_inactive_threads",
    "prepare_awakening_context",
    "update_awakened_thread"
]
