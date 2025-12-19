"""
Conversation Preservation Heuristics

评估对话质量以决定是否值得保存到长期记忆
"""

from libs.types import MessageParams
from utils import get_component_logger

logger = get_component_logger(__name__)


def conversation_quality_evaluator(messages: MessageParams) -> tuple[bool, dict]:
    """
    评估对话是否值得保存

    Args:
        messages: 消息列表

    Returns:
        tuple: (should_preserve, evaluation_details)
            - should_preserve: 是否应该保存
            - evaluation_details: 评估详情字典
    """
    evaluation = {
        "passed_checks": [],
        "failed_checks": []
    }

    # Rule 1: 用户参与度
    user_messages = [m for m in messages if m.role == "user"]
    if len(user_messages) < 2:
        evaluation["failed_checks"].append("insufficient_user_engagement")
        logger.debug(f"用户消息数不足: {len(user_messages)} < 2")
        return False, evaluation

    evaluation["passed_checks"].append("user_engagement")

    # Rule 2: 消息质量 - 平均长度
    total_length = 0
    for msg in user_messages:
        if isinstance(msg.content, str):
            total_length += len(msg.content)
        elif isinstance(msg.content, list):
            # 处理多模态内容
            for item in msg.content:
                if item.type == 'text':
                    total_length += len(item.content)

    avg_user_length = total_length / len(user_messages)

    if avg_user_length < 5:
        evaluation["failed_checks"].append(f"messages_too_short_avg={avg_user_length:.1f}")
        logger.debug(f"用户消息平均长度过短: {avg_user_length:.1f} < 5")
        return False, evaluation

    evaluation["passed_checks"].append("message_quality")

    return True, evaluation
