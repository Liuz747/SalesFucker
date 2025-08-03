"""
响应处理器模块

该模块负责处理LLM响应数据，包括格式转换、兼容性处理和响应验证。
提供统一的响应处理接口，确保API兼容性。

核心功能:
- 响应格式标准化
- 兼容性处理
- 流式响应处理
- 响应数据验证
"""

import json
from typing import Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime

from ..base_provider import LLMResponse
from ..intelligent_router import RoutingStrategy
from src.utils import get_component_logger


class ResponseProcessor:
    """
    响应处理器
    
    负责处理和转换LLM响应数据，确保向后兼容性。
    """
    
    def __init__(self):
        """初始化响应处理器"""
        self.logger = get_component_logger(__name__, "ResponseProcessor")
    
    def process_chat_response(
        self,
        response: Union[LLMResponse, AsyncGenerator[str, None]],
        stream: bool = False
    ) -> Union[str, LLMResponse, AsyncGenerator[str, None]]:
        """
        处理聊天完成响应
        
        参数:
            response: 原始响应
            stream: 是否流式响应
            
        返回:
            Union[str, LLMResponse, AsyncGenerator]: 处理后的响应
        """
        if stream:
            return response  # 流式响应直接返回生成器
        elif isinstance(response, LLMResponse):
            return response.content  # 兼容原有字符串返回格式
        else:
            return response
    
    def process_sentiment_response(
        self,
        response: str
    ) -> Dict[str, Any]:
        """
        处理情感分析响应
        
        参数:
            response: 原始响应字符串
            
        返回:
            Dict[str, Any]: 结构化的情感分析结果
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.warning("情感分析响应JSON解析失败，返回默认值")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            }
    
    def process_intent_response(
        self,
        response: str
    ) -> Dict[str, Any]:
        """
        处理意图分类响应
        
        参数:
            response: 原始响应字符串
            
        返回:
            Dict[str, Any]: 结构化的意图分类结果
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.warning("意图分类响应JSON解析失败，返回默认值")
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "fallback": True
            }
    
    def build_sentiment_messages(self, text: str) -> list:
        """
        构建情感分析消息
        
        参数:
            text: 要分析的文本
            
        返回:
            list: 标准化的消息列表
        """
        return [
            {
                "role": "system",
                "content": "分析给定文本的情感。用JSON格式回复，包含'sentiment'(positive/negative/neutral)、'score'(-1.0到1.0)和'confidence'(0.0到1.0)。"
            },
            {
                "role": "user",
                "content": text
            }
        ]
    
    def build_intent_messages(
        self,
        text: str,
        conversation_history: Optional[list] = None
    ) -> list:
        """
        构建意图分类消息
        
        参数:
            text: 要分类的文本
            conversation_history: 对话历史
            
        返回:
            list: 标准化的消息列表
        """
        context = ""
        if conversation_history:
            context = f"对话历史：\n{chr(10).join(conversation_history[-3:])}\n\n"
        
        return [
            {
                "role": "system",
                "content": "分类美妆咨询的客户意图。用JSON格式回复，包含'intent'(browsing/interested/ready_to_buy/support)、'category'(skincare/makeup/fragrance/general)、'confidence'(0.0-1.0)和'urgency'(low/medium/high)。"
            },
            {
                "role": "user",
                "content": f"{context}客户消息: {text}"
            }
        ]
    
    def get_sentiment_strategy(self) -> RoutingStrategy:
        """获取情感分析的推荐路由策略"""
        return RoutingStrategy.CHINESE_OPTIMIZED
    
    def get_intent_strategy(self) -> RoutingStrategy:
        """获取意图分析的推荐路由策略"""
        return RoutingStrategy.AGENT_OPTIMIZED
    
    def get_sentiment_params(self) -> Dict[str, Any]:
        """获取情感分析的推荐参数"""
        return {
            "temperature": 0.3,
            "max_tokens": 512
        }
    
    def get_intent_params(self) -> Dict[str, Any]:
        """获取意图分析的推荐参数"""
        return {
            "temperature": 0.3,
            "max_tokens": 512
        }
    
    def validate_response(
        self,
        response: Any,
        expected_type: str = "string"
    ) -> bool:
        """
        验证响应格式
        
        参数:
            response: 响应对象
            expected_type: 期望的类型
            
        返回:
            bool: 验证是否通过
        """
        try:
            if expected_type == "string":
                return isinstance(response, str) and len(response) > 0
            elif expected_type == "json":
                if isinstance(response, str):
                    json.loads(response)
                    return True
                elif isinstance(response, dict):
                    return True
                return False
            elif expected_type == "llm_response":
                return isinstance(response, LLMResponse)
            else:
                return response is not None
        except Exception as e:
            self.logger.error(f"响应验证失败: {str(e)}")
            return False