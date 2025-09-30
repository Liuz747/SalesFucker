"""
响应解析器模块

提供统一的LLM响应解析和错误处理功能。
所有智能体可以使用此模块来清洗和解析JSON响应。
"""

import json
import re
from typing import Dict, Any, Optional
from utils import get_component_logger

logger = get_component_logger(__name__)


def parse_json_response(
    response: str,
    default_result: Optional[Dict[str, Any]] = None,
    required_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从LLM响应中提取并解析JSON

    该函数尝试从LLM响应文本中提取JSON内容并解析。
    如果解析失败，返回提供的默认结果或空字典。

    参数:
        response: LLM响应文本
        default_result: 解析失败时返回的默认结果字典
        required_fields: 必需字段及其默认值的字典

    返回:
        Dict[str, Any]: 解析后的JSON数据，如果失败则返回默认值

    示例:
        >>> parse_json_response('{"status": "ok"}')
        {'status': 'ok'}

        >>> parse_json_response('invalid json', {'status': 'error'})
        {'status': 'error', 'fallback': True}
    """
    try:
        # 尝试提取JSON内容 (支持markdown代码块)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)

            # 如果提供了必需字段，确保它们存在
            if required_fields:
                for key, default_value in required_fields.items():
                    if key not in result:
                        result[key] = default_value

            return result

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"JSON解析失败: {e}")

    # 返回默认响应
    fallback_result = default_result or {}
    fallback_result["fallback"] = True
    return fallback_result
