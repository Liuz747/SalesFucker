
class AgentNodes:
    """
    工作流常量类

    定义工作流相关的常量。
    """

    # 节点名称
    COMPLIANCE_NODE = "compliance_review"
    SENTIMENT_NODE = "sentiment_analysis"
    INTENT_NODE = "intent_analysis"
    SALES_NODE = "sales_agent"

    # 触发事件节点
    TRIGGER_INACTIVE = "trigger_inactive"
    TRIGGER_ENGAGEMENT = "trigger_engagement"
