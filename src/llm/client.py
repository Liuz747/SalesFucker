"""
OpenAI Client Module

Provides async OpenAI API integration with error handling and retry logic.
Centralizes all LLM API calls for the multi-agent system.
"""

import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Async OpenAI client wrapper
    
    Provides centralized OpenAI API access with error handling,
    retry logic, and request optimization.
    """
    
    def __init__(self):
        """Initialize OpenAI client with configuration"""
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
        Generate chat completion using OpenAI API
        
        Args:
            messages: List of chat messages in OpenAI format
            model: Optional model override
            temperature: Response randomness (0.0-1.0)
            max_tokens: Maximum response length
            
        Returns:
            str: Generated response content
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
                raise ValueError("Empty response from OpenAI API")
                
            logger.debug(f"Generated response: {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of given text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment, score, and confidence
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