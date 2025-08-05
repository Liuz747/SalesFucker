"""
智能体偏好配置模块

该模块定义了多智能体系统中各个智能体的LLM偏好配置。
专为美妆行业MAS系统优化，为不同类型的智能体提供专业化的LLM配置。

核心功能:
- 智能体类型到LLM偏好的映射
- 路由策略配置
- 模型参数优化
- 供应商选择策略
"""

from typing import Dict, Any, List
from src.llm.intelligent_router import RoutingStrategy


# 智能体LLM偏好配置映射
AGENT_LLM_PREFERENCES = {
    "compliance": {
        "description": "合规审查智能体 - 需要高精度、低温度的法规分析",
        "preferred_providers": ["anthropic", "openai"],  # 精确分析
        "routing_strategy": RoutingStrategy.PERFORMANCE_FIRST,
        "temperature": 0.3,
        "max_tokens": 2048,
        "cost_priority": 0.3,  # 质量优先
        "quality_threshold": 0.9
    },
    "sentiment": {
        "description": "情感分析智能体 - 需要理解中文情感细节",
        "preferred_providers": ["openai", "gemini"],  # 中文情感理解
        "routing_strategy": RoutingStrategy.AGENT_OPTIMIZED,
        "temperature": 0.4,
        "max_tokens": 1024,
        "cost_priority": 0.4,
        "quality_threshold": 0.85
    },
    "intent": {
        "description": "意图分析智能体 - 快速准确的意图识别",
        "preferred_providers": ["gemini", "openai"],  # 快速响应
        "routing_strategy": RoutingStrategy.COST_FIRST,
        "temperature": 0.3,
        "max_tokens": 512,
        "cost_priority": 0.6,  # 成本优化
        "quality_threshold": 0.8
    },
    "sales": {
        "description": "销售智能体 - 创造性对话和个性化推荐",
        "preferred_providers": ["openai", "gemini"],  # 创造性对话
        "routing_strategy": RoutingStrategy.BALANCED,
        "temperature": 0.7,
        "max_tokens": 4096,
        "cost_priority": 0.4,
        "quality_threshold": 0.85
    },
    "product": {
        "description": "产品专家智能体 - 专业产品分析和推荐",
        "preferred_providers": ["anthropic", "gemini"],  # 深度分析
        "routing_strategy": RoutingStrategy.PERFORMANCE_FIRST,
        "temperature": 0.5,
        "max_tokens": 3072,
        "cost_priority": 0.3,  # 质量优先
        "quality_threshold": 0.9
    },
    "memory": {
        "description": "记忆智能体 - 客户信息结构化存储",
        "preferred_providers": ["gemini", "openai"],  # 结构化处理
        "routing_strategy": RoutingStrategy.COST_FIRST,
        "temperature": 0.2,
        "max_tokens": 1024,
        "cost_priority": 0.8,  # 成本优化
        "quality_threshold": 0.7
    },
    "suggestion": {
        "description": "AI建议智能体 - 系统优化和改进建议",
        "preferred_providers": ["anthropic", "openai"],  # 深度思考
        "routing_strategy": RoutingStrategy.AGENT_OPTIMIZED,
        "temperature": 0.4,
        "max_tokens": 2048,
        "cost_priority": 0.5,
        "quality_threshold": 0.85
    },
    "proactive": {
        "description": "主动营销智能体 - 创造性营销内容生成",
        "preferred_providers": ["openai", "gemini"],  # 创造性内容
        "routing_strategy": RoutingStrategy.BALANCED,
        "temperature": 0.6,
        "max_tokens": 2048,
        "cost_priority": 0.4,
        "quality_threshold": 0.8
    },
    "market": {
        "description": "市场策略协调智能体 - 策略分析和规划",
        "preferred_providers": ["anthropic", "gemini"],  # 战略思考
        "routing_strategy": RoutingStrategy.PERFORMANCE_FIRST,
        "temperature": 0.5,
        "max_tokens": 3072,
        "cost_priority": 0.3,
        "quality_threshold": 0.9
    }
}

# 默认偏好配置（用于未定义的智能体类型）
DEFAULT_AGENT_PREFERENCES = {
    "description": "默认智能体配置",
    "preferred_providers": ["openai", "anthropic", "gemini"],
    "routing_strategy": RoutingStrategy.AGENT_OPTIMIZED,
    "temperature": 0.7,
    "max_tokens": 2048,
    "cost_priority": 0.5,
    "quality_threshold": 0.8
}

# 智能体类型特定的系统消息指导原则
AGENT_SYSTEM_GUIDELINES = {
    "compliance": "请确保所有回复符合相关法规要求，避免夸大宣传。",
    "sentiment": "请准确分析客户情感，关注情感变化和满意度。",
    "intent": "请准确识别客户意图，判断购买倾向和紧急程度。",
    "sales": "请提供专业的销售建议，关注客户需求匹配。",
    "product": "请基于产品知识库提供准确的产品信息和推荐。",
    "memory": "请帮助记录和整理重要的客户信息。",
    "suggestion": "请提供建设性的优化建议和改进方案。",
    "proactive": "请生成吸引人的主动营销内容和个性化推荐。",
    "market": "请提供专业的市场策略分析和规划建议。"
}


def get_agent_preferences(agent_type: str) -> Dict[str, Any]:
    """
    获取指定智能体类型的LLM偏好配置
    
    参数:
        agent_type: 智能体类型 (从agent_id中提取)
        
    返回:
        Dict[str, Any]: 智能体的LLM偏好配置
    """
    return AGENT_LLM_PREFERENCES.get(agent_type, DEFAULT_AGENT_PREFERENCES).copy()


def get_agent_system_guideline(agent_type: str) -> str:
    """
    获取指定智能体类型的系统消息指导原则
    
    参数:
        agent_type: 智能体类型
        
    返回:
        str: 系统消息指导原则
    """
    return AGENT_SYSTEM_GUIDELINES.get(agent_type, "请提供专业、友好的回复。")


def get_preferred_providers(agent_type: str) -> List[str]:
    """
    获取指定智能体类型的首选供应商列表
    
    参数:
        agent_type: 智能体类型
        
    返回:
        List[str]: 首选供应商列表
    """
    preferences = get_agent_preferences(agent_type)
    return preferences.get("preferred_providers", ["openai", "anthropic", "gemini"])


def get_routing_strategy(agent_type: str) -> RoutingStrategy:
    """
    获取指定智能体类型的路由策略
    
    参数:
        agent_type: 智能体类型
        
    返回:
        RoutingStrategy: 路由策略
    """
    preferences = get_agent_preferences(agent_type)
    return preferences.get("routing_strategy", RoutingStrategy.AGENT_OPTIMIZED)


def validate_agent_preferences() -> bool:
    """
    验证智能体偏好配置的完整性
    
    返回:
        bool: 配置是否有效
    """
    required_keys = ["preferred_providers", "routing_strategy", "temperature", "max_tokens"]
    
    for agent_type, preferences in AGENT_LLM_PREFERENCES.items():
        for key in required_keys:
            if key not in preferences:
                return False
    
    return True


# 导出配置验证结果
CONFIG_VALID = validate_agent_preferences()