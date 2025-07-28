"""
客户需求评估模块

该模块负责分析客户输入并识别其美容需求。
专注于需求分析逻辑，支持智能推荐。

核心功能:
- 客户需求识别
- 皮肤问题分析
- 产品偏好分析
- 购买意图评估
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum


class SkinType(Enum):
    """皮肤类型枚举"""
    OILY = "oily"
    DRY = "dry"
    COMBINATION = "combination"
    SENSITIVE = "sensitive"
    NORMAL = "normal"


class ConversationStage(Enum):
    """对话阶段枚举"""
    GREETING = "greeting"
    CONSULTATION = "consultation"
    PRODUCT_INQUIRY = "product_inquiry"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"


def analyze_customer_needs(customer_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    分析客户输入以识别美容需求
    
    参数:
        customer_input: 客户输入文本
        context: 对话上下文
        
    返回:
        Dict[str, Any]: 需求分析结果
    """
    if context is None:
        context = {}
    
    needs = {
        "skin_concerns": [],
        "product_interests": [],
        "skin_type_indicators": [],
        "urgency": "normal",
        "budget_signals": [],
        "experience_level": "intermediate"
    }
    
    # 分析皮肤问题
    skin_concerns = _extract_skin_concerns(customer_input)
    needs["skin_concerns"] = skin_concerns
    
    # 分析产品兴趣
    product_interests = _extract_product_interests(customer_input)
    needs["product_interests"] = product_interests
    
    # 分析皮肤类型指标
    skin_type = _detect_skin_type(customer_input)
    needs["skin_type_indicators"] = skin_type
    
    # 分析紧急程度
    urgency = _detect_urgency(customer_input)
    needs["urgency"] = urgency
    
    # 分析预算信号
    budget_signals = _extract_budget_signals(customer_input)
    needs["budget_signals"] = budget_signals
    
    # 分析经验水平
    experience = _assess_experience_level(customer_input)
    needs["experience_level"] = experience
    
    return needs


def determine_conversation_stage(customer_input: str, conversation_history: List[str] = None) -> ConversationStage:
    """
    确定当前对话阶段
    
    参数:
        customer_input: 客户输入
        conversation_history: 对话历史
        
    返回:
        ConversationStage: 对话阶段
    """
    if conversation_history is None:
        conversation_history = []
    
    # 问候阶段标识
    greeting_patterns = [
        r"\b(hi|hello|hey|good morning|good afternoon)\b",
        r"\b(looking for|need help|help me)\b",
        r"^.{1,20}$"  # 短消息通常是问候
    ]
    
    # 产品询问阶段标识
    product_patterns = [
        r"\b(what about|tell me about|how does|what is)\b",
        r"\b(ingredients|benefits|results|price)\b",
        r"\b(recommend|suggest|best)\b"
    ]
    
    # 异议处理阶段标识
    objection_patterns = [
        r"\b(expensive|too much|not sure|skeptical)\b",
        r"\b(doesn't work|tried before|disappointed)\b",
        r"\b(thinking about|need time|maybe later)\b"
    ]
    
    # 结束阶段标识
    closing_patterns = [
        r"\b(okay|sounds good|I'll take|yes|sure)\b",
        r"\b(thank you|thanks|appreciate)\b",
        r"\b(ready to buy|purchase|order)\b"
    ]
    
    input_lower = customer_input.lower()
    
    # 检查各阶段模式
    if any(re.search(pattern, input_lower) for pattern in closing_patterns):
        return ConversationStage.CLOSING
    elif any(re.search(pattern, input_lower) for pattern in objection_patterns):
        return ConversationStage.OBJECTION_HANDLING
    elif any(re.search(pattern, input_lower) for pattern in product_patterns):
        return ConversationStage.PRODUCT_INQUIRY
    elif any(re.search(pattern, input_lower) for pattern in greeting_patterns) and len(conversation_history) < 2:
        return ConversationStage.GREETING
    else:
        return ConversationStage.CONSULTATION


def _extract_skin_concerns(text: str) -> List[str]:
    """提取皮肤问题关键词"""
    concerns_patterns = {
        "acne": r"\b(acne|pimples|breakouts|blemishes|spots)\b",
        "dryness": r"\b(dry|flaky|tight|dehydrated|rough)\b",
        "oiliness": r"\b(oily|shiny|greasy|sebum)\b",
        "sensitivity": r"\b(sensitive|irritated|reactive|red|burning)\b",
        "aging": r"\b(wrinkles|fine lines|aging|sagging|firmness)\b",
        "dark_spots": r"\b(dark spots|hyperpigmentation|uneven|discoloration)\b",
        "large_pores": r"\b(pores|enlarged pores|blackheads)\b"
    }
    
    found_concerns = []
    text_lower = text.lower()
    
    for concern, pattern in concerns_patterns.items():
        if re.search(pattern, text_lower):
            found_concerns.append(concern)
    
    return found_concerns


def _extract_product_interests(text: str) -> List[str]:
    """提取产品兴趣关键词"""
    product_patterns = {
        "skincare": r"\b(skincare|serum|moisturizer|cleanser|toner)\b",
        "makeup": r"\b(makeup|foundation|lipstick|mascara|eyeshadow)\b",
        "sunscreen": r"\b(sunscreen|SPF|sun protection)\b",
        "anti_aging": r"\b(anti-aging|retinol|vitamin C|peptides)\b",
        "acne_treatment": r"\b(salicylic acid|benzoyl peroxide|acne treatment)\b"
    }
    
    interests = []
    text_lower = text.lower()
    
    for product, pattern in product_patterns.items():
        if re.search(pattern, text_lower):
            interests.append(product)
    
    return interests


def _detect_skin_type(text: str) -> List[str]:
    """检测皮肤类型指标"""
    type_patterns = {
        "oily": r"\b(oily|shiny|greasy|T-zone)\b",
        "dry": r"\b(dry|flaky|tight|rough)\b",
        "combination": r"\b(combination|mixed|T-zone dry)\b",
        "sensitive": r"\b(sensitive|reactive|irritated)\b"
    }
    
    indicators = []
    text_lower = text.lower()
    
    for skin_type, pattern in type_patterns.items():
        if re.search(pattern, text_lower):
            indicators.append(skin_type)
    
    return indicators


def _detect_urgency(text: str) -> str:
    """检测紧急程度"""
    high_urgency_patterns = [
        r"\b(urgent|emergency|ASAP|immediately|right now)\b",
        r"\b(event|wedding|party|tomorrow|tonight)\b",
        r"\b(running out|need today|desperate)\b"
    ]
    
    low_urgency_patterns = [
        r"\b(browsing|looking around|just curious)\b",
        r"\b(maybe|thinking about|considering)\b",
        r"\b(no rush|whenever|eventually)\b"
    ]
    
    text_lower = text.lower()
    
    if any(re.search(pattern, text_lower) for pattern in high_urgency_patterns):
        return "high"
    elif any(re.search(pattern, text_lower) for pattern in low_urgency_patterns):
        return "low"
    else:
        return "normal"


def _extract_budget_signals(text: str) -> List[str]:
    """提取预算信号"""
    budget_patterns = {
        "budget_conscious": r"\b(cheap|affordable|budget|inexpensive|deal)\b",
        "luxury_oriented": r"\b(luxury|premium|high-end|expensive|invest)\b",
        "value_focused": r"\b(value|worth it|quality|best bang)\b"
    }
    
    signals = []
    text_lower = text.lower()
    
    for signal, pattern in budget_patterns.items():
        if re.search(pattern, text_lower):
            signals.append(signal)
    
    return signals


def _assess_experience_level(text: str) -> str:
    """评估经验水平"""
    beginner_patterns = [
        r"\b(new to|beginner|don't know|never used)\b",
        r"\b(help me|guide me|what should|how do I)\b"
    ]
    
    expert_patterns = [
        r"\b(usually use|always|typically|my routine)\b",
        r"\b(ingredients|formula|concentration)\b",
        r"\b(tried|experienced|know about)\b"
    ]
    
    text_lower = text.lower()
    
    if any(re.search(pattern, text_lower) for pattern in beginner_patterns):
        return "beginner"
    elif any(re.search(pattern, text_lower) for pattern in expert_patterns):
        return "advanced"
    else:
        return "intermediate" 