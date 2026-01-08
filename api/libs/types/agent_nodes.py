from enum import StrEnum


class AgentNodeType(StrEnum):
    """
    Agent节点类型

    定义工作流中可用的Agent节点标识符。
    """

    # 核心分析节点
    CHAT = "chat_agent"
    COMPLIANCE = "compliance_review"
    SENTIMENT = "sentiment_analysis"
    INTENT = "intent_analysis"
    SALES = "sales_agent"

    # 触发事件节点
    TRIGGER_INACTIVE = "trigger_inactive"
    TRIGGER_ENGAGEMENT = "trigger_engagement"
