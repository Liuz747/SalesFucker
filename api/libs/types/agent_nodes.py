from enum import StrEnum


class AgentNodeType(StrEnum):
    """
    工作流智能体节点类型枚举

    定义工作流中可用的智能体节点标识符。
    """

    # 核心分析节点
    CHAT = "chat"
    COMPLIANCE = "compliance_review"
    SENTIMENT = "sentiment_analysis"
    INTENT = "intent_analysis"
    SALES = "sales_agent"

    # 触发事件节点
    TRIGGER_INACTIVE = "trigger_inactive"
    TRIGGER_ENGAGEMENT = "trigger_engagement"
