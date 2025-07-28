"""
销售智能体模块

该模块包含销售智能体的所有组件，采用模块化设计。
遵循trunk-based development最佳实践，将功能分散到专注的小模块中。

模块组织:
- conversation_templates.py: 对话模板管理
- sales_strategies.py: 销售策略和客户细分
- need_assessment.py: 客户需求分析
- ../sales.py: 轻量级核心智能体
"""

from .agent import SalesAgent
from .conversation_templates import get_conversation_templates, get_conversation_responses, get_tone_variations
from .sales_strategies import get_sales_strategies, analyze_customer_segment, CustomerSegment
from .need_assessment import analyze_customer_needs, determine_conversation_stage, ConversationStage, SkinType

# 公开接口
__all__ = [
    # 核心智能体
    "SalesAgent",
    
    # 模板和响应管理
    "get_conversation_templates",
    "get_conversation_responses", 
    "get_tone_variations",
    
    # 策略管理
    "get_sales_strategies",
    "analyze_customer_segment",
    "CustomerSegment",
    
    # 需求分析
    "analyze_customer_needs",
    "determine_conversation_stage",
    "ConversationStage",
    "SkinType"
] 