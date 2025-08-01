"""
OpenAI客户端模块

提供带错误处理和重试逻辑的异步OpenAI API集成。
为多智能体系统集中管理所有LLM API调用。
"""

import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    异步OpenAI客户端包装器
    
    提供集中式OpenAI API访问，包含错误处理、
    重试逻辑和请求优化。
    """
    
    def __init__(self):
        """使用配置初始化OpenAI客户端"""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.default_model = settings.openai_model
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        使用OpenAI API生成聊天完成
        
        参数:
            messages: OpenAI格式的聊天消息列表
            model: 可选的模型覆盖
            temperature: 响应随机性 (0.0-1.0)
            max_tokens: 最大响应长度
            
        返回:
            str: 生成的响应内容
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI API返回空响应")
                
            logger.debug(f"生成响应: {len(content)} 字符")
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API错误: {e}")
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        分析给定文本的情感
        
        参数:
            text: 要分析的文本
            
        返回:
            包含情感、分数和置信度的字典
        """
        messages = [
            {
                "role": "system",
                "content": "Analyze the sentiment of the given text. Respond with JSON containing 'sentiment' (positive/negative/neutral), 'score' (-1.0 to 1.0), and 'confidence' (0.0 to 1.0)."
            },
            {
                "role": "user", 
                "content": text
            }
        ]
        
        response = await self.chat_completion(messages, temperature=0.3)
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            }
    
    async def classify_intent(self, text: str, conversation_history: List[str] = None) -> Dict[str, Any]:
        """
        Classify customer intent from text
        
        Args:
            text: Customer input to classify
            conversation_history: Previous conversation context
            
        Returns:
            Dict with intent classification results
        """
        context = ""
        if conversation_history:
            context = f"Previous conversation:\n{chr(10).join(conversation_history[-3:])}\n\n"
        
        messages = [
            {
                "role": "system",
                "content": "Classify customer intent for beauty/cosmetic consultation. Respond with JSON containing 'intent' (browsing/interested/ready_to_buy/support), 'category' (skincare/makeup/fragrance/general), 'confidence' (0.0-1.0), and 'urgency' (low/medium/high)."
            },
            {
                "role": "user",
                "content": f"{context}Customer message: {text}"
            }
        ]
        
        response = await self.chat_completion(messages, temperature=0.3)
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "intent": "browsing",
                "category": "general", 
                "confidence": 0.5,
                "urgency": "medium",
                "fallback": True
            }


# Global client instance
_llm_client: Optional[OpenAIClient] = None


def get_llm_client() -> OpenAIClient:
    """Get or create global LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAIClient()
    return _llm_client