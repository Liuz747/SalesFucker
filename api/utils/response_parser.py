"""
结构化响应解析工具

该模块提供用于解析LLM结构化响应的通用工具函数。
支持JSON格式响应的提取、验证和错误处理。

核心功能:
- JSON响应提取和解析
- 字段验证和默认值填充
- 错误处理和降级策略
- 多种响应格式支持
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from utils import get_component_logger


logger = get_component_logger(__name__, "ResponseParser")


def parse_structured_response(
    response: str, 
    response_type: str,
    required_fields: Optional[List[str]] = None,
    default_values: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    解析LLM结构化响应
    
    参数:
        response: LLM响应文本
        response_type: 响应类型（用于日志记录）
        required_fields: 必需字段列表
        default_values: 字段默认值映射
        
    返回:
        Dict[str, Any]: 解析后的结构化数据
    """
    try:
        # 尝试提取JSON内容
        json_str = extract_json_from_text(response)
        if not json_str:
            logger.warning(f"{response_type}响应中未找到有效JSON: {response[:100]}...")
            return get_default_response(response_type, default_values)
        
        # 解析JSON
        result = json.loads(json_str)
        
        # 验证和填充字段
        if required_fields:
            result = validate_and_fill_fields(result, required_fields, default_values)
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"{response_type}响应JSON解析失败: {e}")
        return get_default_response(response_type, default_values)
    except Exception as e:
        logger.error(f"{response_type}响应解析异常: {e}")
        return get_default_response(response_type, default_values)


def extract_json_from_text(text: str) -> Optional[str]:
    """
    从文本中提取JSON字符串
    
    参数:
        text: 包含JSON的文本
        
    返回:
        提取的JSON字符串，失败返回None
    """
    # 尝试多种JSON提取模式
    patterns = [
        r'\{[^{}]*\}',  # 简单JSON对象
        r'\{.*?\}',     # 非贪婪匹配
        r'\{.*\}',      # 贪婪匹配（可能包含嵌套）
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                # 验证是否为有效JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
    
    return None


def validate_and_fill_fields(
    data: Dict[str, Any], 
    required_fields: List[str],
    default_values: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    验证并填充必需字段
    
    参数:
        data: 原始数据
        required_fields: 必需字段列表
        default_values: 字段默认值
        
    返回:
        验证并填充后的数据
    """
    if default_values is None:
        default_values = {}
    
    for field in required_fields:
        if field not in data or data[field] is None:
            data[field] = default_values.get(field, get_default_field_value(field))
    
    return data


def get_default_field_value(field: str) -> Any:
    """
    获取字段的通用默认值
    
    参数:
        field: 字段名
        
    返回:
        字段默认值
    """
    # 常见字段的默认值
    field_defaults = {
        "status": "unknown",
        "score": 0.0,
        "confidence": 0.0,
        "violations": [],
        "issues": [],
        "recommendations": [],
        "severity": "low",
        "priority": "low",
        "user_message": "",
        "message": "",
        "recommended_action": "proceed",
        "action": "proceed",
        "category": "general",
        "type": "general",
        "sentiment": "neutral",
        "emotion": "neutral",
        "intent": "unknown",
        "needs": [],
        "preferences": {}
    }
    
    return field_defaults.get(field, "")


def get_default_response(
    response_type: str, 
    custom_defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    获取特定响应类型的默认响应
    
    参数:
        response_type: 响应类型
        custom_defaults: 自定义默认值
        
    返回:
        默认响应数据
    """
    # 响应类型特定的默认值
    type_defaults = {
        "compliance": {
            "status": "approved",
            "violations": [],
            "severity": "low",
            "user_message": "",
            "recommended_action": "proceed",
            "parse_error": True
        },
        "sentiment": {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotions": [],
            "satisfaction": 0.5,
            "urgency": 0.3,
            "parse_error": True
        },
        "intent": {
            "intent": "inquiry",
            "confidence": 0.5,
            "needs": [],
            "priority": "medium",
            "next_action": "continue",
            "parse_error": True
        }
    }
    
    # 获取类型默认值
    defaults = type_defaults.get(response_type, {
        "status": "unknown",
        "parse_error": True
    })
    
    # 应用自定义默认值
    if custom_defaults:
        defaults.update(custom_defaults)
    
    return defaults


def parse_compliance_response(response: str) -> Dict[str, Any]:
    """解析合规检查响应"""
    required_fields = ["status", "violations", "severity", "user_message", "recommended_action"]
    return parse_structured_response(response, "compliance", required_fields)


def parse_sentiment_response(response: str) -> Dict[str, Any]:
    """解析情感分析响应"""
    required_fields = ["sentiment", "confidence", "emotions", "satisfaction", "urgency"]
    return parse_structured_response(response, "sentiment", required_fields)


def parse_intent_response(response: str) -> Dict[str, Any]:
    """解析意图分析响应"""
    required_fields = ["intent", "confidence", "needs", "priority", "next_action"]
    return parse_structured_response(response, "intent", required_fields)