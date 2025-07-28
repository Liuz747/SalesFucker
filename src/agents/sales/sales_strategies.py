"""
销售策略管理模块

该模块负责化妆品销售策略的定义和管理。
专注于策略逻辑，支持动态策略选择。

核心功能:
- 销售策略定义
- 策略选择逻辑  
- 客户分析和分类
- 动态策略调整
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class CustomerSegment(Enum):
    """客户细分类型"""
    PREMIUM = "premium"
    BUDGET = "budget"
    YOUTH = "youth"
    MATURE = "mature"
    PROFESSIONAL = "professional"


def get_sales_strategies() -> Dict[str, Dict[str, Any]]:
    """
    获取销售策略配置
    
    返回:
        Dict[str, Dict[str, Any]]: 销售策略字典
    """
    return {
        "premium": {
            "tone": "sophisticated",
            "focus": "luxury_experience",
            "approach": "consultative",
            "key_benefits": ["exclusivity", "premium_ingredients", "professional_results"],
            "conversation_style": "refined",
            "product_positioning": "investment_in_beauty",
            "objection_strategy": "value_demonstration"
        },
        
        "budget": {
            "tone": "friendly",
            "focus": "value_for_money",
            "approach": "solution_oriented",
            "key_benefits": ["effectiveness", "affordability", "multi_purpose"],
            "conversation_style": "practical",
            "product_positioning": "smart_choice",
            "objection_strategy": "cost_benefit_analysis"
        },
        
        "youth": {
            "tone": "energetic",
            "focus": "trends_and_fun",
            "approach": "discovery_based",
            "key_benefits": ["trending", "instagram_worthy", "experimentation"],
            "conversation_style": "casual",
            "product_positioning": "self_expression",
            "objection_strategy": "social_proof"
        },
        
        "mature": {
            "tone": "warm",
            "focus": "proven_results",
            "approach": "trust_building",
            "key_benefits": ["anti_aging", "skin_health", "gentle_formulation"],
            "conversation_style": "respectful",
            "product_positioning": "age_appropriate_care",
            "objection_strategy": "expert_recommendation"
        },
        
        "professional": {
            "tone": "professional",
            "focus": "efficiency_and_quality",
            "approach": "time_efficient",
            "key_benefits": ["long_lasting", "professional_grade", "time_saving"],
            "conversation_style": "direct",
            "product_positioning": "professional_tool",
            "objection_strategy": "performance_metrics"
        }
    }


def analyze_customer_segment(customer_profile: Dict[str, Any]) -> CustomerSegment:
    """
    分析客户档案，确定客户细分
    
    参数:
        customer_profile: 客户档案信息
        
    返回:
        CustomerSegment: 客户细分类型
    """
    age = customer_profile.get("age", 0)
    budget_preference = customer_profile.get("budget_preference", "medium")
    lifestyle = customer_profile.get("lifestyle", "")
    purchase_history = customer_profile.get("purchase_history", [])
    
    # 根据年龄进行初步分类
    if age < 25:
        base_segment = CustomerSegment.YOUTH
    elif age > 50:
        base_segment = CustomerSegment.MATURE
    else:
        base_segment = CustomerSegment.PROFESSIONAL
    
    # 根据预算偏好调整
    if budget_preference == "high" or "luxury" in purchase_history:
        return CustomerSegment.PREMIUM
    elif budget_preference == "low":
        return CustomerSegment.BUDGET
    
    # 根据生活方式调整
    if "business" in lifestyle or "corporate" in lifestyle:
        return CustomerSegment.PROFESSIONAL
    
    return base_segment


def get_strategy_for_segment(segment: CustomerSegment) -> Dict[str, Any]:
    """
    获取指定客户细分的销售策略
    
    参数:
        segment: 客户细分类型
        
    返回:
        Dict[str, Any]: 销售策略配置
    """
    strategies = get_sales_strategies()
    return strategies.get(segment.value, strategies["professional"])


def adapt_strategy_to_context(base_strategy: Dict[str, Any], 
                            conversation_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据对话上下文调整销售策略
    
    参数:
        base_strategy: 基础销售策略
        conversation_context: 对话上下文
        
    返回:
        Dict[str, Any]: 调整后的销售策略
    """
    adapted_strategy = base_strategy.copy()
    
    # 根据客户情绪调整语调
    sentiment = conversation_context.get("sentiment", "neutral")
    if sentiment == "negative":
        adapted_strategy["tone"] = "empathetic"
        adapted_strategy["approach"] = "problem_solving"
    elif sentiment == "excited":
        adapted_strategy["tone"] = "enthusiastic"
    
    # 根据紧急程度调整策略
    urgency = conversation_context.get("urgency", "normal")
    if urgency == "high":
        adapted_strategy["approach"] = "direct"
        adapted_strategy["focus"] = "immediate_solution"
    
    # 根据购买意图调整
    intent = conversation_context.get("purchase_intent", "browsing")
    if intent == "ready_to_buy":
        adapted_strategy["approach"] = "closing_focused"
    elif intent == "researching":
        adapted_strategy["approach"] = "educational"
    
    return adapted_strategy


def get_conversation_stage_strategy(stage: str, customer_segment: CustomerSegment) -> Dict[str, Any]:
    """
    获取特定对话阶段的策略
    
    参数:
        stage: 对话阶段
        customer_segment: 客户细分
        
    返回:
        Dict[str, Any]: 阶段策略配置
    """
    base_strategy = get_strategy_for_segment(customer_segment)
    
    stage_strategies = {
        "greeting": {
            "priority": "rapport_building",
            "goals": ["welcome", "understand_needs"],
            "tone_adjustment": "warm"
        },
        "consultation": {
            "priority": "need_assessment", 
            "goals": ["identify_concerns", "gather_preferences"],
            "tone_adjustment": "professional"
        },
        "product_inquiry": {
            "priority": "education",
            "goals": ["explain_benefits", "demonstrate_value"],
            "tone_adjustment": "confident"
        },
        "objection_handling": {
            "priority": "reassurance",
            "goals": ["address_concerns", "build_trust"],
            "tone_adjustment": "empathetic"
        },
        "closing": {
            "priority": "conversion",
            "goals": ["summarize_benefits", "encourage_purchase"],
            "tone_adjustment": "encouraging"
        }
    }
    
    stage_config = stage_strategies.get(stage, stage_strategies["consultation"])
    
    # 合并基础策略和阶段策略
    combined_strategy = base_strategy.copy()
    combined_strategy.update(stage_config)
    
    return combined_strategy 