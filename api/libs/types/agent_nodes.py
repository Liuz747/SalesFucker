from enum import StrEnum


class AgentNodeType(StrEnum):
    """
    Agent节点类型

    定义工作流中可用的Agent节点标识符。
    """

    # 核心分析节点
    COMPLIANCE = "compliance_review"
    INTENT = "intent_analysis"
    SALES = "sales_agent"
    SENTIMENT = "sentiment_analysis"
    TEST_CHAT = "test_chat"

    # 触发事件节点
    TRIGGER_INACTIVE = "trigger_inactive"
    TRIGGER_ENGAGEMENT = "trigger_engagement"
