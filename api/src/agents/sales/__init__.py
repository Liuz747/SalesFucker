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
from .sales_strategies import get_sales_strategies, analyze_customer_segment, CustomerSegment
# Need assessment now handled by enhanced IntentAnalysisAgent with LLM field extraction

# 公开接口
__all__ = [
    # 核心智能体
    "SalesAgent",
    
    # 模板和响应管理 (now LLM-powered)
    
    # 策略管理
    "get_sales_strategies",
    "analyze_customer_segment",
    "CustomerSegment"
    
    # 需求分析现在由增强的IntentAnalysisAgent处理
] 