
class AgentNodes:
    """
    工作流常量类

    定义工作流相关的常量。
    """

    # 节点名称
    COMPLIANCE_NODE = "compliance_review"
    SENTIMENT_NODE = "sentiment_analysis"
    INTENT_NODE = "intent_analysis"
    STRATEGY_NODE = "market_strategy"
    SALES_NODE = "sales_agent"
    PRODUCT_NODE = "product_expert"

    # 新增并行节点
    APPOINTMENT_INTENT_NODE = "appointment_intent_analysis"
    MATERIAL_INTENT_NODE = "material_intent_analysis"
